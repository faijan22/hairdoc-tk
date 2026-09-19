from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import DeviceSession, User


@override_settings(DEBUG=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AuthenticationFlowTests(APITestCase):
    email = "client@example.com"
    password = "HairDoc!2026Strong"

    def register_and_verify(self) -> User:
        register = self.client.post(
            reverse("accounts:register"),
            {"email": self.email, "password": self.password, "first_name": "Client"},
            format="json",
        )
        self.assertEqual(register.status_code, 202)
        self.assertEqual(len(mail.outbox), 1)
        token = register.json()["debug_verification_token"]
        verify = self.client.post(reverse("accounts:verify-email"), {"token": token}, format="json")
        self.assertEqual(verify.status_code, 200)
        return User.objects.get(normalized_email=self.email)

    def login(self, password=None, device_name="Test phone"):
        return self.client.post(
            reverse("accounts:login"),
            {"email": self.email, "password": password or self.password, "device_name": device_name},
            format="json",
        )

    def authorize(self, access_token: str) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

    def test_register_verify_login_refresh_and_reuse_revokes_family(self):
        register = self.client.post(
            reverse("accounts:register"),
            {"email": "Client@Example.COM", "password": self.password},
            format="json",
        )
        self.assertEqual(register.status_code, 202)
        user = User.objects.get()
        self.assertEqual(user.email, self.email)
        self.assertFalse(user.is_email_verified)
        self.assertEqual(self.login().status_code, 403)

        token = register.json()["debug_verification_token"]
        self.assertEqual(self.client.post(reverse("accounts:verify-email"), {"token": token}, format="json").status_code, 200)
        self.assertEqual(self.client.post(reverse("accounts:verify-email"), {"token": token}, format="json").status_code, 400)

        login = self.login()
        self.assertEqual(login.status_code, 200)
        first_refresh = login.json()["refresh_token"]
        self.authorize(login.json()["access_token"])
        self.assertEqual(self.client.get(reverse("accounts:me")).status_code, 200)
        self.client.credentials()

        refresh = self.client.post(reverse("accounts:refresh"), {"refresh_token": first_refresh}, format="json")
        self.assertEqual(refresh.status_code, 200)
        reuse = self.client.post(reverse("accounts:refresh"), {"refresh_token": first_refresh}, format="json")
        self.assertEqual(reuse.status_code, 401)
        self.assertEqual(DeviceSession.objects.get().revoke_reason, "REFRESH_REUSE")

        self.authorize(refresh.json()["access_token"])
        self.assertEqual(self.client.get(reverse("accounts:me")).status_code, 401)

    def test_web_refresh_rotates_in_http_only_cookie_and_logout_clears_it(self):
        cache.clear()
        self.register_and_verify()
        login = self.client.post(
            reverse("accounts:login"),
            {
                "email": self.email,
                "password": self.password,
                "device_name": "Web browser",
            },
            format="json",
            HTTP_X_HAIRDOC_CLIENT="web",
        )
        self.assertEqual(login.status_code, 200)
        self.assertNotIn("refresh_token", login.json())
        cookie = login.cookies["hairdoc_refresh"]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        first_cookie = cookie.value

        refreshed = self.client.post(
            reverse("accounts:refresh"),
            {},
            format="json",
            HTTP_X_HAIRDOC_CLIENT="web",
        )
        self.assertEqual(refreshed.status_code, 200)
        self.assertNotIn("refresh_token", refreshed.json())
        self.assertNotEqual(
            refreshed.cookies["hairdoc_refresh"].value,
            first_cookie,
        )

        logged_out = self.client.post(
            reverse("accounts:logout"),
            {},
            format="json",
            HTTP_X_HAIRDOC_CLIENT="web",
        )
        self.assertEqual(logged_out.status_code, 204)
        self.assertEqual(logged_out.cookies["hairdoc_refresh"]["max-age"], 0)

    def test_password_reset_is_generic_single_use_and_revokes_sessions(self):
        self.register_and_verify()
        login = self.login()
        self.assertEqual(login.status_code, 200)

        unknown = self.client.post(
            reverse("accounts:forgot-password"),
            {"email": "unknown@example.com"},
            format="json",
        )
        self.assertEqual(unknown.status_code, 200)
        self.assertNotIn("debug_reset_token", unknown.json())

        forgot = self.client.post(reverse("accounts:forgot-password"), {"email": self.email}, format="json")
        reset_token = forgot.json()["debug_reset_token"]
        new_password = "NewHairDoc!2026Strong"
        reset = self.client.post(
            reverse("accounts:reset-password"),
            {"token": reset_token, "new_password": new_password},
            format="json",
        )
        self.assertEqual(reset.status_code, 200)
        self.assertEqual(
            self.client.post(
                reverse("accounts:reset-password"),
                {"token": reset_token, "new_password": "Another!2026Strong"},
                format="json",
            ).status_code,
            400,
        )
        self.assertFalse(DeviceSession.objects.get().is_active)
        self.assertEqual(self.login().status_code, 401)
        self.assertEqual(self.login(password=new_password).status_code, 200)

    def test_session_list_revoke_and_logout_all_are_user_scoped(self):
        self.register_and_verify()
        first = self.login(device_name="Phone").json()
        second = self.login(device_name="Desktop").json()
        self.authorize(first["access_token"])

        sessions = self.client.get(reverse("accounts:sessions"))
        self.assertEqual(sessions.status_code, 200)
        self.assertEqual(len(sessions.json()), 2)
        other = next(item for item in sessions.json() if not item["is_current"])
        self.assertEqual(
            self.client.delete(reverse("accounts:session-detail", kwargs={"public_id": other["public_id"]})).status_code,
            204,
        )

        self.assertEqual(self.client.post(reverse("accounts:logout-all")).status_code, 204)
        self.assertEqual(self.client.get(reverse("accounts:me")).status_code, 401)
        self.client.credentials()
        self.assertEqual(
            self.client.post(reverse("accounts:refresh"), {"refresh_token": second["refresh_token"]}, format="json").status_code,
            401,
        )

    def test_verified_registration_response_does_not_reissue_token(self):
        self.register_and_verify()
        response = self.client.post(
            reverse("accounts:register"),
            {"email": self.email, "password": "Different!2026Strong"},
            format="json",
        )
        self.assertEqual(response.status_code, 202)
        self.assertNotIn("debug_verification_token", response.json())
