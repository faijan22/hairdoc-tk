from django.test import TestCase

from apps.accounts.models import User


class UserModelTests(TestCase):
    def test_manager_normalizes_email(self):
        user = User.objects.create_user("Person@Example.COM", "test-password")

        self.assertEqual(user.email, "person@example.com")
        self.assertEqual(user.normalized_email, "person@example.com")
        self.assertTrue(user.check_password("test-password"))

