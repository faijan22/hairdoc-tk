from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import ClientHairProfile

from .models import ConsultationAnswer, ConsultationCase, ConsultationResponse, QuestionnaireQuestion
from .selectors import current_questionnaire, published_services


class IntakeError(Exception):
    def __init__(self, details):
        self.details = details
        super().__init__("The intake could not be completed.")


def _hair_profile_snapshot(user) -> dict:
    try:
        profile = user.hair_profile
    except ClientHairProfile.DoesNotExist:
        return {}
    return {
        "hair_texture": profile.hair_texture,
        "scalp_type": profile.scalp_type,
        "concerns": profile.concerns[:500],
        "goals": profile.goals[:500],
        "current_routine": profile.current_routine[:1000],
    }


def _questionnaire_is_ready(questionnaire) -> bool:
    questions = list(questionnaire.questions.prefetch_related("options"))
    if not questions:
        return False
    keys = {question.key for question in questions}
    for question in questions:
        if question.show_if_question_key and question.show_if_question_key not in keys:
            return False
        if question.type in (
            QuestionnaireQuestion.Type.SINGLE_CHOICE,
            QuestionnaireQuestion.Type.MULTI_CHOICE,
        ) and not question.options.exists():
            return False
    return True


@transaction.atomic
def start_consultation(client, service_public_id, timezone_name: str):
    if client.is_staff:
        raise IntakeError({"account": ["Staff accounts cannot start client consultations."]})
    try:
        ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        raise IntakeError({"timezone": ["Use a valid IANA timezone, for example Europe/London."]}) from None

    service = published_services().filter(public_id=service_public_id).first()
    if not service:
        raise IntakeError({"service_public_id": ["This consultation service is unavailable."]})
    existing = ConsultationCase.objects.filter(client=client, service=service, status=ConsultationCase.Status.DRAFT).first()
    if existing:
        return existing, False
    questionnaire = current_questionnaire(service)
    if not questionnaire or not _questionnaire_is_ready(questionnaire):
        raise IntakeError({"service_public_id": ["This service’s intake is still being prepared."]})
    try:
        with transaction.atomic():
            case = ConsultationCase.objects.create(
                client=client,
                service=service,
                timezone_snapshot=timezone_name,
                hair_profile_snapshot=_hair_profile_snapshot(client),
                service_name=service.name,
                duration_minutes=service.duration_minutes,
                price_amount=service.price_amount,
                currency=service.currency,
            )
    except IntegrityError:
        return ConsultationCase.objects.get(client=client, service=service, status=ConsultationCase.Status.DRAFT), False
    ConsultationResponse.objects.create(case=case, questionnaire=questionnaire)
    return case, True


def _blank(value) -> bool:
    return value is None or value == "" or value == []


def validate_answer(question: QuestionnaireQuestion, value):
    if _blank(value):
        return None
    if question.type in (QuestionnaireQuestion.Type.SHORT_TEXT, QuestionnaireQuestion.Type.LONG_TEXT):
        if not isinstance(value, str):
            raise ValueError("Enter text.")
        limit = question.max_length or (500 if question.type == QuestionnaireQuestion.Type.SHORT_TEXT else 5000)
        value = value.strip()
        if len(value) > limit:
            raise ValueError(f"Use {limit} characters or fewer.")
        return value
    if question.type == QuestionnaireQuestion.Type.BOOLEAN:
        if not isinstance(value, bool):
            raise ValueError("Choose Yes or No.")
        return value
    if question.type == QuestionnaireQuestion.Type.DATE:
        if not isinstance(value, str):
            raise ValueError("Enter a date as YYYY-MM-DD.")
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError:
            raise ValueError("Enter a valid date as YYYY-MM-DD.") from None
    allowed = set(question.options.values_list("value", flat=True))
    if question.type == QuestionnaireQuestion.Type.SINGLE_CHOICE:
        if not isinstance(value, str) or value not in allowed:
            raise ValueError("Choose one of the available options.")
        return value
    if question.type == QuestionnaireQuestion.Type.MULTI_CHOICE:
        if not isinstance(value, list) or len(value) > 20 or any(not isinstance(item, str) for item in value):
            raise ValueError("Choose valid available options.")
        unique = list(dict.fromkeys(value))
        if any(item not in allowed for item in unique):
            raise ValueError("Choose valid available options.")
        return unique
    raise ValueError("This question type is unsupported.")


@transaction.atomic
def save_answers(case: ConsultationCase, submitted_answers: list[dict]):
    case = ConsultationCase.objects.select_for_update().get(pk=case.pk)
    if case.status != ConsultationCase.Status.DRAFT:
        raise IntakeError({"case": ["This intake is complete and can no longer be edited."]})
    questions = {
        question.key: question
        for question in case.response.questionnaire.questions.prefetch_related("options")
    }
    errors = {}
    validated = []
    seen = set()
    for item in submitted_answers:
        key = item["question_key"]
        if key in seen:
            errors[key] = ["Send each question only once."]
            continue
        seen.add(key)
        question = questions.get(key)
        if not question:
            errors[key] = ["This question is not part of the assigned intake."]
            continue
        try:
            validated.append((question, validate_answer(question, item.get("value"))))
        except ValueError as exc:
            errors[key] = [str(exc)]
    if errors:
        raise IntakeError(errors)
    for question, value in validated:
        if value is None:
            ConsultationAnswer.objects.filter(response=case.response, question=question).delete()
        else:
            ConsultationAnswer.objects.update_or_create(
                response=case.response,
                question=question,
                defaults={"value": value},
            )
    case.save(update_fields=("updated_at",))
    return case


def _is_visible(question: QuestionnaireQuestion, values: dict) -> bool:
    if not question.show_if_question_key:
        return True
    dependency = values.get(question.show_if_question_key)
    expected = question.show_if_value.lower()
    if isinstance(dependency, list):
        return any(str(item).lower() == expected for item in dependency)
    return str(dependency).lower() == expected


@transaction.atomic
def complete_intake(case: ConsultationCase):
    case = ConsultationCase.objects.select_for_update().get(pk=case.pk)
    if case.status == ConsultationCase.Status.INTAKE_COMPLETE:
        return case
    if case.status != ConsultationCase.Status.DRAFT:
        raise IntakeError({"case": ["This intake cannot be completed from its current state."]})
    values = {answer.question.key: answer.value for answer in case.response.answers.select_related("question")}
    errors = {}
    for question in case.response.questionnaire.questions.all():
        if question.required and _is_visible(question, values) and _blank(values.get(question.key)):
            errors[question.key] = ["This answer is required."]
    if errors:
        raise IntakeError(errors)
    case.status = ConsultationCase.Status.INTAKE_COMPLETE
    case.intake_completed_at = timezone.now()
    case.save(update_fields=("status", "intake_completed_at", "updated_at"))
    return case
