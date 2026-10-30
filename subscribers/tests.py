import hashlib
import time
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from config.csp import CSP_ADMIN, CSP_HEADER, CSP_STRICT

from .models import Subscriber
from .views import (
    EMAIL_MAX_LENGTH,
    FORM_TS_MAX_AGE,
    FORM_TS_MIN_AGE,
    make_form_ts,
)


def _aged_form_ts(age_seconds):
    """Signed form_ts as if the page was rendered `age_seconds` ago."""
    return make_form_ts(now=time.time() - age_seconds)


def _valid_form_ts():
    return _aged_form_ts(FORM_TS_MIN_AGE + 1)


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
        self.assertContains(response, 'name="form_ts"')
        self.assertContains(response, 'maxlength="254"')
        self.assertContains(response, 'href="/privacy/"')
        self.assertContains(response, "політикою конфіденційності")

    def test_json_ld_present(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'type="application/ld+json"')
        self.assertContains(response, '"@type": "Organization"')
        self.assertContains(response, '"@type": "WebSite"')
        self.assertContains(response, "https://gestia-home.com/#organization")
        self.assertContains(response, "/static/assets/img/icon-512.png")
        self.assertContains(response, 'rel="manifest" href="/site.webmanifest"')


@override_settings(
    DEBUG=True,
    ADMIN_URL="admin-local/",
    SECURE_SSL_REDIRECT=False,
)
class SeoEndpointsTests(TestCase):
    def test_sitemap_xml(self):
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertIn("xml", response["Content-Type"])
        body = response.content.decode()
        self.assertIn("https://gestia-home.com/", body)
        self.assertIn("https://gestia-home.com/privacy/", body)
        self.assertNotIn("admin", body.lower())

    def test_site_webmanifest(self):
        response = self.client.get("/site.webmanifest")
        self.assertEqual(response.status_code, 200)
        self.assertIn("manifest", response["Content-Type"])
        data = response.json()
        self.assertEqual(data["name"], "Gestia Home")
        srcs = {icon["src"] for icon in data["icons"]}
        self.assertIn("/static/assets/img/icon-192.png", srcs)
        self.assertIn("/static/assets/img/icon-512.png", srcs)

    def test_robots_txt_has_sitemap(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Allow: /", body)
        self.assertIn("Sitemap: https://gestia-home.com/sitemap.xml", body)
        self.assertNotIn("admin", body.lower())


@override_settings(
    DEBUG=True,
    ADMIN_URL="admin-local/",
    SECURE_SSL_REDIRECT=False,
)
class PrivacyTests(TestCase):
    def test_privacy_page_renders(self):
        response = self.client.get(reverse("privacy"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Політика конфіденційності")
        self.assertContains(response, "хеш IP")
        self.assertContains(response, "12 місяців")
        self.assertContains(response, "privacy@gestia-home.com")


@override_settings(
    DEBUG=True,
    ADMIN_URL="admin-local/",
    SECURE_SSL_REDIRECT=False,
)
class SubscribeTests(TestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("subscribe")
        self.form_ts = _valid_form_ts()

    def _payload(self, extra=None):
        data = {"form_ts": self.form_ts}
        if extra:
            data.update(extra)
        return data

    def _post_json(self, payload, **extra):
        return self.client.post(
            self.url,
            data=self._payload(payload),
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
        self.assertFalse(hasattr(sub, "user_agent"))

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

    def test_email_longer_than_254_rejected(self):
        local = "a" * (EMAIL_MAX_LENGTH - len("@example.com") + 1)
        email = f"{local}@example.com"
        self.assertGreater(len(email), EMAIL_MAX_LENGTH)
        response = self._post_json({"email": email})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])
        self.assertEqual(Subscriber.objects.count(), 0)

    def test_honeypot_200_no_rows(self):
        response = self._post_json(
            {"email": "bot@example.com", "website": "http://spam.test"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(Subscriber.objects.count(), 0)

    def test_time_trap_too_fast_silent_success(self):
        fast_ts = _aged_form_ts(0)
        response = self.client.post(
            self.url,
            data={"email": "fast@example.com", "form_ts": fast_ts},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(Subscriber.objects.count(), 0)

    def test_time_trap_missing_silent_success(self):
        response = self.client.post(
            self.url,
            data={"email": "missing-ts@example.com"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(Subscriber.objects.count(), 0)

    def test_time_trap_invalid_signature_silent_success(self):
        response = self.client.post(
            self.url,
            data={"email": "bad-sig@example.com", "form_ts": "not-a-valid-token"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(Subscriber.objects.count(), 0)

    def test_time_trap_expired_silent_success(self):
        expired = _aged_form_ts(FORM_TS_MAX_AGE + 10)
        response = self.client.post(
            self.url,
            data={"email": "old@example.com", "form_ts": expired},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(Subscriber.objects.count(), 0)

    @patch("subscribers.views.time.time")
    def test_time_trap_valid_after_min_age_with_freeze(self, mock_time):
        rendered = 1_700_000_000.0
        mock_time.return_value = rendered
        token = make_form_ts()
        mock_time.return_value = rendered + FORM_TS_MIN_AGE + 1
        response = self.client.post(
            self.url,
            data={"email": "ok-trap@example.com", "form_ts": token},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(Subscriber.objects.count(), 1)

    def test_rate_limit_429(self):
        for i in range(5):
            res = self._post_json({"email": f"user{i}@example.com"})
            self.assertIn(res.status_code, (200, 400))
        response = self._post_json({"email": "overflow@example.com"})
        self.assertEqual(response.status_code, 429)
        self.assertFalse(response.json()["ok"])

    def test_x_real_ip_used_for_hash(self):
        response = self._post_json(
            {"email": "realip@example.com"},
            HTTP_X_FORWARDED_FOR="1.2.3.4",
            HTTP_X_REAL_IP="9.8.7.6",
        )
        self.assertEqual(response.status_code, 200)
        sub = Subscriber.objects.get()
        expected = hashlib.sha256(
            f"{settings.IP_HASH_SALT}9.8.7.6".encode()
        ).hexdigest()
        self.assertEqual(sub.ip_hash, expected)

    def test_x_forwarded_for_ignored_falls_back_to_remote_addr(self):
        response = self._post_json(
            {"email": "spoof@example.com"},
            HTTP_X_FORWARDED_FOR="1.2.3.4",
            REMOTE_ADDR="127.0.0.1",
        )
        self.assertEqual(response.status_code, 200)
        sub = Subscriber.objects.get()
        expected = hashlib.sha256(
            f"{settings.IP_HASH_SALT}127.0.0.1".encode()
        ).hexdigest()
        self.assertEqual(sub.ip_hash, expected)
        spoofed = hashlib.sha256(
            f"{settings.IP_HASH_SALT}1.2.3.4".encode()
        ).hexdigest()
        self.assertNotEqual(sub.ip_hash, spoofed)

    def _post_form(self, payload, **extra):
        return self.client.post(self.url, data=self._payload(payload), **extra)

    def test_nojs_valid_submit_redirects_subscribed(self):
        response = self._post_form({"email": "form@example.com"})
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response["Location"], "/?subscribed=1")
        self.assertEqual(Subscriber.objects.count(), 1)
        follow = self.client.get("/?subscribed=1")
        self.assertEqual(follow.status_code, 200)
        self.assertContains(follow, "Дякуємо!")
        self.assertContains(follow, 'id="form-status"')

    def test_nojs_invalid_email_redirects_error(self):
        response = self._post_form({"email": "not-an-email"})
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response["Location"], "/?error=invalid")
        self.assertEqual(Subscriber.objects.count(), 0)
        follow = self.client.get("/?error=invalid")
        self.assertEqual(follow.status_code, 200)
        self.assertContains(follow, "Будь ласка, введіть коректний e-mail")
        self.assertContains(follow, "hero__status--error")

    def test_nojs_rate_limit_redirects_error_rate(self):
        for i in range(5):
            res = self._post_form({"email": f"form{i}@example.com"})
            self.assertEqual(res.status_code, 303)
        response = self._post_form({"email": "overflow-form@example.com"})
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response["Location"], "/?error=rate")
        follow = self.client.get("/?error=rate")
        self.assertEqual(follow.status_code, 200)
        self.assertContains(follow, "Забагато спроб")


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


@override_settings(
    DEBUG=True,
    ADMIN_URL="admin-local/",
    SECURE_SSL_REDIRECT=False,
)
class ContentSecurityPolicyTests(TestCase):
    def test_home_has_strict_csp(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response[CSP_HEADER], CSP_STRICT)
        self.assertNotIn("unsafe-inline", response[CSP_HEADER])
        self.assertNotIn("unsafe-eval", response[CSP_HEADER])

    def test_admin_login_has_relaxed_csp(self):
        response = self.client.get(f"/{settings.ADMIN_URL}login/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response[CSP_HEADER], CSP_ADMIN)
        self.assertIn("unsafe-inline", response[CSP_HEADER])
        self.assertIn("unsafe-eval", response[CSP_HEADER])
