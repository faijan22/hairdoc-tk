from django.urls import path

from .views import (
    AccountDeletionView,
    ChangePasswordView,
    ConsentListUpdateView,
    ForgotPasswordView,
    HairProfileView,
    LoginView,
    LegalDocumentListView,
    LegalDocumentFileView,
    LogoutAllView,
    LogoutView,
    MeView,
    NotificationPreferenceView,
    RefreshView,
    RegisterView,
    ResendVerificationView,
    ResetPasswordView,
    SessionDetailView,
    SessionListView,
    CurrentLegalDocumentView,
    VerifyEmailView,
)

app_name = "accounts"

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/refresh/", RefreshView.as_view(), name="refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/logout-all/", LogoutAllView.as_view(), name="logout-all"),
    path("auth/email/verify/", VerifyEmailView.as_view(), name="verify-email"),
    path("auth/email/resend/", ResendVerificationView.as_view(), name="resend-email"),
    path("auth/password/forgot/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("auth/password/reset/", ResetPasswordView.as_view(), name="reset-password"),
    path("auth/password/change/", ChangePasswordView.as_view(), name="change-password"),
    path("me/", MeView.as_view(), name="me"),
    path("me/account/delete/", AccountDeletionView.as_view(), name="account-delete"),
    path("me/hair-profile/", HairProfileView.as_view(), name="hair-profile"),
    path("me/notification-preferences/", NotificationPreferenceView.as_view(), name="notification-preferences"),
    path("me/consents/", ConsentListUpdateView.as_view(), name="consents"),
    path("me/sessions/", SessionListView.as_view(), name="sessions"),
    path("me/sessions/<uuid:public_id>/", SessionDetailView.as_view(), name="session-detail"),
    path("legal/", LegalDocumentListView.as_view(), name="legal-list"),
    path("legal/<str:document_type>/current/", CurrentLegalDocumentView.as_view(), name="legal-current"),
    path("legal/documents/<uuid:public_id>/file/", LegalDocumentFileView.as_view(), name="legal-file"),
]
