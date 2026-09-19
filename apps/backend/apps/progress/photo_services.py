import hashlib
import uuid
from pathlib import Path

from django.core import signing
from django.db import transaction

from apps.accounts.models import User, UserConsent
from apps.consultations.photo_services import active_photo_consent, current_photo_document, normalize_private_image, photo_consent_required
from apps.private_media.models import StoredFile
from apps.private_media.storage import get_storage_provider

from .models import ProgressCheckIn, ProgressPhoto, ProgressPhotoAccess

MAX_PHOTOS_PER_CHECK_IN = 6
TOKEN_MAX_AGE_SECONDS = 300
TOKEN_SALT = "hairdoc.private-progress-photo.v1"


class ProgressPhotoError(Exception):
    def __init__(self, details):
        self.details = details
        super().__init__("The progress photo request could not be completed.")


def create_progress_photo(check_in, uploaded_file, category):
    content, width, height = normalize_private_image(uploaded_file)
    provider = get_storage_provider()
    storage_key = f"progress/{check_in.public_id}/{uuid.uuid4()}.jpg"
    provider.save(storage_key, content)
    try:
        with transaction.atomic():
            locked = ProgressCheckIn.objects.select_for_update().select_related("client").get(pk=check_in.pk)
            if locked.status != ProgressCheckIn.Status.DRAFT:
                raise ProgressPhotoError({"check_in": ["Submitted check-in photos cannot be changed."]})
            if locked.photos.count() >= MAX_PHOTOS_PER_CHECK_IN:
                raise ProgressPhotoError({"photos": [f"You can add up to {MAX_PHOTOS_PER_CHECK_IN} photos."]})
            document = current_photo_document()
            consent = active_photo_consent(locked.client, document)
            if photo_consent_required() and (not document or not consent):
                raise ProgressPhotoError({"consent": ["Accept the current Photo & Data Consent before uploading."]})
            stored = StoredFile.objects.create(owner=locked.client, storage_key=storage_key, original_name=Path(uploaded_file.name or "progress-photo.jpg").name[:255], content_type="image/jpeg", byte_size=len(content), checksum_sha256=hashlib.sha256(content).hexdigest(), width=width, height=height)
            return ProgressPhoto.objects.create(check_in=locked, stored_file=stored, category=category, consent_document=document if consent else None, consent_accepted_at=consent.accepted_at if consent else None)
    except Exception:
        provider.delete(storage_key)
        raise


@transaction.atomic
def delete_progress_photo(photo):
    check_in = ProgressCheckIn.objects.select_for_update().get(pk=photo.check_in_id)
    if check_in.status != ProgressCheckIn.Status.DRAFT:
        raise ProgressPhotoError({"check_in": ["Submitted check-in photos cannot be changed."]})
    stored = photo.stored_file
    key = stored.storage_key
    photo.delete()
    stored.delete()
    transaction.on_commit(lambda: get_storage_provider().delete(key))


def issue_progress_photo_token(photo, viewer):
    case = photo.check_in.case
    if viewer.pk != photo.check_in.client_id and (not viewer.is_staff or case.service.expert_id != viewer.pk):
        raise ProgressPhotoError({"photo": ["You do not have access to this private photo."]})
    consent_valid = photo.consent_document_id and UserConsent.objects.filter(user=photo.check_in.client, legal_document=photo.consent_document, withdrawn_at__isnull=True).exists()
    if not consent_valid and photo_consent_required():
        raise ProgressPhotoError({"consent": ["The client has withdrawn photo access consent."]})
    return signing.dumps({"photo": str(photo.public_id), "viewer": str(viewer.public_id)}, salt=TOKEN_SALT, compress=True)


def resolve_progress_photo(token):
    try:
        payload = signing.loads(token, salt=TOKEN_SALT, max_age=TOKEN_MAX_AGE_SECONDS)
        viewer = User.objects.get(public_id=payload["viewer"], is_active=True)
        photo = ProgressPhoto.objects.select_related("check_in__client", "check_in__case__service", "stored_file", "consent_document").get(public_id=payload["photo"])
    except (signing.BadSignature, signing.SignatureExpired, KeyError, User.DoesNotExist, ProgressPhoto.DoesNotExist):
        raise ProgressPhotoError({"token": ["This private photo link is invalid or expired."]}) from None
    purpose = ProgressPhotoAccess.Purpose.CLIENT_VIEW if viewer.pk == photo.check_in.client_id else ProgressPhotoAccess.Purpose.STAFF_REVIEW
    if viewer.pk != photo.check_in.client_id and (not viewer.is_staff or photo.check_in.case.service.expert_id != viewer.pk):
        raise ProgressPhotoError({"photo": ["You do not have access to this private photo."]})
    consent_valid = photo.consent_document_id and UserConsent.objects.filter(user=photo.check_in.client, legal_document=photo.consent_document, withdrawn_at__isnull=True).exists()
    if not consent_valid and photo_consent_required():
        raise ProgressPhotoError({"consent": ["The client has withdrawn photo access consent."]})
    return photo, viewer, purpose
