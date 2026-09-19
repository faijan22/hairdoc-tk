import mimetypes

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import FileResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import ClientHairProfile, EmailActionToken, LegalDocument, NotificationPreference, User, UserConsent
from .serializers import (
    AccountDeletionSerializer,
    ChangePasswordSerializer,
    ClientHairProfileSerializer,
    ConsentUpdateSerializer,
    DeviceSessionSerializer,
    EmailSerializer,
    LoginSerializer,
    LegalDocumentSerializer,
    NotificationPreferenceSerializer,
    RefreshSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    TokenSerializer,
    UserSerializer,
    UserConsentSerializer,
)
from .services import (
    AccountDeletionError,
    InvalidActionToken,
    InvalidRefreshToken,
    create_device_session,
    delete_client_account,
    issue_email_action,
    register_client,
    reset_password,
    revoke_all_user_sessions,
    revoke_session,
    revoke_session_by_refresh,
    rotate_refresh_token,
    verify_email,
)


GENERIC_EMAIL_MESSAGE = "If the account is eligible, an email has been sent."


class AuthRejected(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication credentials were invalid."
    default_code = "authentication_rejected"


def _is_web_client(request):
    return request.headers.get("X-HairDoc-Client", "").lower() == "web"


def _token_response(access_token, refresh_token, user, *, include_refresh=True):
    payload = {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": settings.AUTH_ACCESS_TOKEN_MINUTES * 60,
        "user": UserSerializer(user).data,
    }
    if include_refresh:
        payload["refresh_token"] = refresh_token
    return payload


def _set_web_refresh_cookie(response, request, refresh_token):
    if _is_web_client(request):
        response.set_cookie(
            settings.AUTH_REFRESH_COOKIE_NAME,
            refresh_token,
            max_age=settings.AUTH_REFRESH_TOKEN_DAYS * 24 * 60 * 60,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax",
            path=settings.AUTH_REFRESH_COOKIE_PATH,
        )
    return response


def _clear_web_refresh_cookie(response):
    response.delete_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
        samesite="Lax",
    )
    return response


def _refresh_token_from_request(request):
    if _is_web_client(request):
        return request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME, "")
    return request.data.get("refresh_token", "")


def _debug_token(payload: dict, key: str, token: str | None) -> dict:
    if settings.DEBUG and token:
        payload[key] = token
    return payload


class PublicAuthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]


class RegisterView(PublicAuthView):
    throttle_scope = "auth_register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            _, token = register_client(**serializer.validated_data)
        except DjangoValidationError as exc:
            raise ValidationError({"password": list(exc.messages)}) from exc
        payload = _debug_token({"message": GENERIC_EMAIL_MESSAGE}, "debug_verification_token", token)
        return Response(payload, status=status.HTTP_202_ACCEPTED)


class VerifyEmailView(PublicAuthView):
    throttle_scope = "auth_token"

    def post(self, request):
        serializer = TokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = verify_email(serializer.validated_data["token"])
        except InvalidActionToken:
            raise ValidationError({"token": ["This verification token is invalid or expired."]}) from None
        return Response({"message": "Email verified.", "user": UserSerializer(user).data})


class ResendVerificationView(PublicAuthView):
    throttle_scope = "auth_recovery"

    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(normalized_email=serializer.validated_data["email"], is_email_verified=False).first()
        token = issue_email_action(user, EmailActionToken.Purpose.VERIFY_EMAIL) if user else None
        return Response(_debug_token({"message": GENERIC_EMAIL_MESSAGE}, "debug_verification_token", token))


class LoginView(PublicAuthView):
    throttle_scope = "auth_login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = authenticate(request=request, username=data["email"], password=data["password"])
        if user is None:
            raise AuthRejected("Invalid email or password.", code="invalid_credentials")
        if not user.is_email_verified:
            raise PermissionDenied("Verify your email before signing in.", code="email_not_verified")
        access, refresh, _ = create_device_session(user, data.get("device_name", ""))
        update_last_login(None, user)
        response = Response(
            _token_response(
                access, refresh, user, include_refresh=not _is_web_client(request)
            )
        )
        return _set_web_refresh_cookie(response, request, refresh)


class RefreshView(PublicAuthView):
    throttle_scope = "auth_token"

    def post(self, request):
        raw_token = _refresh_token_from_request(request)
        if not raw_token:
            raise AuthRejected(
                "The session is invalid or expired.",
                code="invalid_refresh_token",
            )
        serializer = RefreshSerializer(
            data={"refresh_token": raw_token}
        )
        serializer.is_valid(raise_exception=True)
        try:
            access, refresh, session = rotate_refresh_token(serializer.validated_data["refresh_token"])
        except InvalidRefreshToken:
            raise AuthRejected("The session is invalid or expired.", code="invalid_refresh_token") from None
        response = Response(
            _token_response(
                access,
                refresh,
                session.user,
                include_refresh=not _is_web_client(request),
            )
        )
        return _set_web_refresh_cookie(response, request, refresh)


class LogoutView(PublicAuthView):
    throttle_scope = "auth_token"

    def post(self, request):
        raw_token = _refresh_token_from_request(request)
        if raw_token:
            serializer = RefreshSerializer(data={"refresh_token": raw_token})
            serializer.is_valid(raise_exception=True)
            revoke_session_by_refresh(serializer.validated_data["refresh_token"])
        return _clear_web_refresh_cookie(
            Response(status=status.HTTP_204_NO_CONTENT)
        )


class ForgotPasswordView(PublicAuthView):
    throttle_scope = "auth_recovery"

    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(normalized_email=serializer.validated_data["email"], is_email_verified=True).first()
        token = issue_email_action(user, EmailActionToken.Purpose.RESET_PASSWORD) if user else None
        return Response(_debug_token({"message": GENERIC_EMAIL_MESSAGE}, "debug_reset_token", token))


class ResetPasswordView(PublicAuthView):
    throttle_scope = "auth_token"

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            reset_password(serializer.validated_data["token"], serializer.validated_data["new_password"])
        except InvalidActionToken:
            raise ValidationError({"token": ["This reset token is invalid or expired."]}) from None
        except DjangoValidationError as exc:
            raise ValidationError({"new_password": list(exc.messages)}) from exc
        return Response({"message": "Password reset. Sign in with your new password."})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class HairProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, user):
        profile, _ = ClientHairProfile.objects.get_or_create(user=user)
        return profile

    def get(self, request):
        return Response(ClientHairProfileSerializer(self.get_object(request.user)).data)

    def patch(self, request):
        serializer = ClientHairProfileSerializer(self.get_object(request.user), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class NotificationPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, user):
        preferences, _ = NotificationPreference.objects.get_or_create(user=user)
        return preferences

    def get(self, request):
        return Response(NotificationPreferenceSerializer(self.get_object(request.user)).data)

    def patch(self, request):
        serializer = NotificationPreferenceSerializer(self.get_object(request.user), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


def _published_legal_documents():
    return LegalDocument.objects.filter(
        status=LegalDocument.Status.PUBLISHED,
        published_at__isnull=False,
        published_at__lte=timezone.now(),
    )


class LegalDocumentListView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        current = []
        for document_type, _ in LegalDocument.Type.choices:
            document = _published_legal_documents().filter(type=document_type).order_by("-version", "-published_at").first()
            if document:
                current.append(document)
        return Response(LegalDocumentSerializer(current, many=True).data)


class CurrentLegalDocumentView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, document_type):
        valid_types = {value for value, _ in LegalDocument.Type.choices}
        normalized_type = document_type.upper()
        if normalized_type not in valid_types:
            raise NotFound("Legal document not found.", code="legal_document_not_found")
        document = _published_legal_documents().filter(type=normalized_type).order_by("-version", "-published_at").first()
        if not document:
            raise NotFound("Legal document not found.", code="legal_document_not_found")
        return Response(LegalDocumentSerializer(document).data)


class LegalDocumentFileView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, public_id):
        document = _published_legal_documents().filter(public_id=public_id).first()
        if not document or not document.attachment:
            raise NotFound("Legal file not found.", code="legal_file_not_found")
        content_type = mimetypes.guess_type(document.attachment_name)[0] or "application/octet-stream"
        try:
            response = FileResponse(
                document.attachment.open("rb"),
                as_attachment=False,
                filename=document.attachment_name,
                content_type=content_type,
            )
        except OSError:
            raise NotFound("Legal file not found.", code="legal_file_not_found") from None
        response["Cache-Control"] = "public, max-age=300"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class ConsentListUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        consents = request.user.consents.select_related("legal_document")
        return Response(UserConsentSerializer(consents, many=True).data)

    def post(self, request):
        serializer = ConsentUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        document = _published_legal_documents().filter(public_id=data["document_public_id"]).first()
        if not document:
            raise NotFound("Legal document not found.", code="legal_document_not_found")
        now = timezone.now()
        consent, created = UserConsent.objects.get_or_create(
            user=request.user,
            legal_document=document,
            defaults={"accepted_at": now, "withdrawn_at": None if data["accepted"] else now},
        )
        if not created:
            if data["accepted"]:
                consent.accepted_at = now
                consent.withdrawn_at = None
            else:
                consent.withdrawn_at = now
            consent.save(update_fields=("accepted_at", "withdrawn_at"))
        return Response(UserConsentSerializer(consent).data)


class LogoutAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        revoke_all_user_sessions(request.user, "LOGOUT_ALL")
        return _clear_web_refresh_cookie(
            Response(status=status.HTTP_204_NO_CONTENT)
        )


class AccountDeletionView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "account_delete"

    def post(self, request):
        serializer = AccountDeletionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not request.user.check_password(serializer.validated_data["current_password"]):
            raise ValidationError({"current_password": ["The current password is incorrect."]})
        try:
            delete_client_account(request.user)
        except AccountDeletionError as exc:
            raise ValidationError({"account": [str(exc)]}) from None
        return _clear_web_refresh_cookie(
            Response(status=status.HTTP_204_NO_CONTENT)
        )


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if not request.user.check_password(data["current_password"]):
            raise ValidationError({"current_password": ["The current password is incorrect."]})
        request.user.set_password(data["new_password"])
        request.user.save(update_fields=("password", "updated_at"))
        revoke_all_user_sessions(request.user, "PASSWORD_CHANGE")
        return _clear_web_refresh_cookie(
            Response({"message": "Password changed. Sign in again."})
        )


class SessionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = request.user.device_sessions.filter(revoked_at__isnull=True, expires_at__gt=timezone.now())
        serializer = DeviceSessionSerializer(sessions, many=True, context={"current_session": request.auth})
        return Response(serializer.data)


class SessionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, public_id):
        session = request.user.device_sessions.filter(public_id=public_id, revoked_at__isnull=True).first()
        if not session:
            raise NotFound("Session not found.", code="session_not_found")
        revoke_session(session, "USER_REVOKED")
        return Response(status=status.HTTP_204_NO_CONTENT)
