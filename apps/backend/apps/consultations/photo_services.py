import hashlib
import io
import uuid
import warnings
from pathlib import Path

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError

from apps.accounts.models import LegalDocument, User, UserConsent
from apps.private_media.models import StoredFile
from apps.private_media.storage import get_storage_provider

from .models import ConsultationCase, ConsultationPhoto, ConsultationPhotoAccess

MAX_SOURCE_BYTES = 12 * 1024 * 1024
MAX_STORED_BYTES = 8 * 1024 * 1024
MAX_PHOTOS_PER_CASE = 8
MIN_IMAGE_EDGE = 300
MAX_IMAGE_EDGE = 2400
PHOTO_TOKEN_MAX_AGE_SECONDS = 300
PHOTO_TOKEN_SALT = "hairdoc.private-consultation-photo.v1"
SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP"}


class PhotoError(Exception):
    def __init__(self, details):
        self.details = details
        super().__init__("The photo request could not be completed.")


def current_photo_document():
    return (
        LegalDocument.objects.filter(
            type=LegalDocument.Type.PHOTO_DATA_CONSENT,
            status=LegalDocument.Status.PUBLISHED,
            published_at__isnull=False,
            published_at__lte=timezone.now(),
        )
        .order_by("-version", "-published_at")
        .first()
    )


def active_photo_consent(user, document=None):
    document = document or current_photo_document()
    if not document:
        return None
    return UserConsent.objects.filter(
        user=user,
        legal_document=document,
        withdrawn_at__isnull=True,
    ).first()


def photo_consent_required():
    return settings.PHOTO_CONSENT_REQUIRED


def photo_access_allowed(user):
    return not photo_consent_required() or active_photo_consent(user) is not None


def photo_consent_payload(user):
    if not photo_consent_required():
        return {
            "required": False,
            "available": False,
            "accepted": False,
            "document_public_id": None,
            "document_title": "",
            "document_version": None,
        }
    document = current_photo_document()
    consent = active_photo_consent(user, document)
    return {
        "required": True,
        "available": bool(document),
        "accepted": bool(consent),
        "document_public_id": document.public_id if document else None,
        "document_title": document.title if document else "Photo & Data Consent",
        "document_version": document.version if document else None,
    }


def normalize_private_image(uploaded_file):
    if uploaded_file.size > MAX_SOURCE_BYTES:
        raise PhotoError({"file": ["Choose an image smaller than 12 MB."]})
    raw = uploaded_file.read()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as source:
                if source.format not in SUPPORTED_FORMATS:
                    raise PhotoError({"file": ["Use a JPEG, PNG, or WebP image."]})
                source.load()
                normalized = ImageOps.exif_transpose(source)
                if min(normalized.size) < MIN_IMAGE_EDGE:
                    raise PhotoError({"file": ["Choose an image at least 300 pixels on each side."]})
                normalized.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Image.Resampling.LANCZOS)
                if normalized.mode != "RGB":
                    background = Image.new("RGB", normalized.size, "white")
                    if "A" in normalized.getbands():
                        background.paste(normalized, mask=normalized.getchannel("A"))
                    else:
                        background.paste(normalized)
                    normalized = background
                output = io.BytesIO()
                normalized.save(output, format="JPEG", quality=88, optimize=True)
                content = output.getvalue()
                width, height = normalized.size
    except PhotoError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise PhotoError({"file": ["This file is not a valid supported image."]}) from None
    if len(content) > MAX_STORED_BYTES:
        raise PhotoError({"file": ["The processed image is too large. Choose a smaller image."]})
    return content, width, height


def _require_editable_photo_step(case):
    if case.status != ConsultationCase.Status.INTAKE_COMPLETE:
        message = (
            "Complete the private intake before adding photos."
            if case.status == ConsultationCase.Status.DRAFT
            else "Submitted consultation photos can no longer be changed."
        )
        raise PhotoError({"case": [message]})


def create_photo(case, uploaded_file, category):
    content, width, height = normalize_private_image(uploaded_file)
    provider = get_storage_provider()
    storage_key = f"consultations/{case.public_id}/{uuid.uuid4()}.jpg"
    provider.save(storage_key, content)
    try:
        with transaction.atomic():
            locked_case = ConsultationCase.objects.select_for_update().get(pk=case.pk)
            _require_editable_photo_step(locked_case)
            if locked_case.photos.count() >= MAX_PHOTOS_PER_CASE:
                raise PhotoError({"photos": [f"You can add up to {MAX_PHOTOS_PER_CASE} photos."]})
            document = current_photo_document()
            consent = active_photo_consent(locked_case.client, document)
            if photo_consent_required() and (not document or not consent):
                raise PhotoError({"consent": ["Accept the current Photo & Data Consent before uploading."]})
            stored = StoredFile.objects.create(
                owner=locked_case.client,
                storage_key=storage_key,
                original_name=Path(uploaded_file.name or "consultation-photo.jpg").name[:255],
                content_type="image/jpeg",
                byte_size=len(content),
                checksum_sha256=hashlib.sha256(content).hexdigest(),
                width=width,
                height=height,
            )
            photo = ConsultationPhoto.objects.create(
                case=locked_case,
                stored_file=stored,
                uploaded_by=locked_case.client,
                category=category,
                consent_document=document if consent else None,
                consent_accepted_at=consent.accepted_at if consent else None,
            )
            locked_case.save(update_fields=("updated_at",))
            return photo
    except Exception:
        provider.delete(storage_key)
        raise


@transaction.atomic
def delete_photo(photo):
    case = ConsultationCase.objects.select_for_update().get(pk=photo.case_id)
    _require_editable_photo_step(case)
    stored = photo.stored_file
    storage_key = stored.storage_key
    photo.delete()
    stored.delete()
    transaction.on_commit(lambda: get_storage_provider().delete(storage_key))


@transaction.atomic
def complete_photos(case):
    case = ConsultationCase.objects.select_for_update().get(pk=case.pk)
    if case.status == ConsultationCase.Status.PHOTOS_COMPLETE:
        return case
    _require_editable_photo_step(case)
    if not photo_access_allowed(case.client):
        raise PhotoError({"consent": ["Active Photo & Data Consent is required to submit photos."]})
    if not case.photos.exists():
        raise PhotoError({"photos": ["Add at least one clear photo before continuing."]})
    case.status = ConsultationCase.Status.PHOTOS_COMPLETE
    case.photos_completed_at = timezone.now()
    case.save(update_fields=("status", "photos_completed_at", "updated_at"))
    from apps.notifications.services import notify_consultation_submitted

    notify_consultation_submitted(case)
    return case


def issue_photo_access_token(photo, viewer):
    if viewer.pk != photo.case.client_id:
        if not viewer.is_staff or photo.case.status != ConsultationCase.Status.PHOTOS_COMPLETE:
            raise PhotoError({"photo": ["You do not have access to this private photo."]})
        consent_valid = photo.consent_document_id and UserConsent.objects.filter(
            user=photo.case.client, legal_document=photo.consent_document, withdrawn_at__isnull=True,
        ).exists()
        if not consent_valid and photo_consent_required():
            raise PhotoError({"consent": ["The client has withdrawn photo access consent."]})
    return signing.dumps(
        {"photo": str(photo.public_id), "viewer": str(viewer.public_id)},
        salt=PHOTO_TOKEN_SALT,
        compress=True,
    )


def resolve_photo_access(token):
    try:
        payload = signing.loads(token, salt=PHOTO_TOKEN_SALT, max_age=PHOTO_TOKEN_MAX_AGE_SECONDS)
        viewer = User.objects.get(public_id=payload["viewer"], is_active=True)
        photo = ConsultationPhoto.objects.select_related(
            "case__client", "stored_file", "consent_document",
        ).get(public_id=payload["photo"])
    except (signing.BadSignature, signing.SignatureExpired, KeyError, User.DoesNotExist, ConsultationPhoto.DoesNotExist):
        raise PhotoError({"token": ["This private photo link is invalid or expired."]}) from None
    if viewer.pk == photo.case.client_id:
        purpose = ConsultationPhotoAccess.Purpose.CLIENT_VIEW
    elif viewer.is_staff and photo.case.status == ConsultationCase.Status.PHOTOS_COMPLETE:
        consent_valid = photo.consent_document_id and UserConsent.objects.filter(
            user=photo.case.client, legal_document=photo.consent_document, withdrawn_at__isnull=True,
        ).exists()
        if not consent_valid and photo_consent_required():
            raise PhotoError({"consent": ["The client has withdrawn photo access consent."]})
        purpose = ConsultationPhotoAccess.Purpose.STAFF_REVIEW
    else:
        raise PhotoError({"photo": ["You do not have access to this private photo."]})
    return photo, viewer, purpose
