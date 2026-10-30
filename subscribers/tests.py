from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Subscriber


@override_settings(
    DEBUG=True,
    ADMIN_URL="admin-local/",
    SECURE_SSL_REDIRECT=False,
)
class IndexTests(TestCase):
    def test_page_renders_with_form_and_canonical(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="waitlist-form"')
        self.assertContains(response, 'rel="canonical"')
        self.assertContains(response, "https://gestia-home.com/")
        self.assertContains(response, 'name="website"')


@override_settings(
    DEBUG=True,
    ADMIN_URL="admin-local/",
    SECURE_SSL_REDIRECT=False,
)
class SubscribeTests(TestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("subscribe")

    def _post_json(self, payload, **extra):
        return self.client.post(
            self.url,
            data=payload,
            content_type="application/json",
            **extra,
        )

    def test_valid_submit_creates_subscriber(self):
        response = self._post_json({"email": "User@Example.com"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(Subscriber.objects.count(), 1)
        sub = Subscriber.objects.get()
        self.assertEqual(sub.email, "user@example.com")

    def test_duplicate_different_case_success_one_row(self):
        self._post_json({"email": "dup@example.com"})
        response = self._post_json({"email": "DUP@example.com"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(Subscriber.objects.count(), 1)

    def test_invalid_email_400(self):
        response = self._post_json({"email": "not-an-email"})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["ok"])
        self.assertIn("e-mail", data["message"].lower())
        self.assertEqual(Subscriber.objects.count(), 0)

    def test_honeypot_200_no_rows(self):
        response = self._post_json(
            {"email": "bot@example.com", "website": "http://spam.test"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(Subscriber.objects.count(), 0)

    def test_rate_limit_429(self):
        for i in range(5):
            res = self._post_json({"email": f"user{i}@example.com"})
            self.assertIn(res.status_code, (200, 400))
        response = self._post_json({"email": "overflow@example.com"})
        self.assertEqual(response.status_code, 429)
        self.assertFalse(response.json()["ok"])


@override_settings(
    DEBUG=True,
    ADMIN_URL="admin-local/",
    SECURE_SSL_REDIRECT=False,
)
class AdminExportTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="pass12345",
        )
        self.client = Client()
        self.client.force_login(self.user)
        Subscriber.objects.create(email="export@example.com")

    def test_csv_export_action(self):
        url = reverse("admin:subscribers_subscriber_changelist")
        response = self.client.post(
            url,
            {
                "action": "export_csv",
                "_selected_action": [
                    str(pk) for pk in Subscriber.objects.values_list("pk", flat=True)
                ],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        body = response.content.decode("utf-8-sig")
        self.assertIn("email", body)
        self.assertIn("export@example.com", body)
