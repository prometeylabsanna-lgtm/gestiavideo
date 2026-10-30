import hashlib
import json

from django.conf import settings
from django.core.cache import cache
from django.core.validators import EmailValidator
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from .models import Subscriber

SUCCESS_MSG = (
    "Дякуємо! Ми повідомимо тебе першою, щойно бокси стануть доступними."
)
INVALID_MSG = "Будь ласка, введіть коректний e-mail"
RATE_LIMIT_MSG = "Забагато спроб. Спробуйте пізніше."

RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW = 600  # 10 minutes


@method_decorator(ensure_csrf_cookie, name="dispatch")
class IndexView(TemplateView):
    template_name = "index.html"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PrivacyView(TemplateView):
    template_name = "privacy.html"


def _client_ip(request):
    """Trust only X-Real-IP set by nginx; never client-controlled X-Forwarded-For."""
    real_ip = (request.META.get("HTTP_X_REAL_IP") or "").strip()
    if real_ip:
        return real_ip
    return request.META.get("REMOTE_ADDR", "") or ""


def axes_client_ip(request):
    """django-axes IP callback — same source as subscribe rate limit."""
    return _client_ip(request)


def _ip_hash(ip: str) -> str:
    raw = f"{settings.IP_HASH_SALT}{ip}".encode()
    return hashlib.sha256(raw).hexdigest()


def _parse_body(request):
    content_type = request.META.get("CONTENT_TYPE", "")
    if "application/json" in content_type:
        try:
            data = json.loads(request.body.decode() or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        return data
    return request.POST


@require_POST
def subscribe(request):
    data = _parse_body(request)
    email_raw = (data.get("email") or "").strip()
    honeypot = (data.get("website") or "").strip()

    ip = _client_ip(request)
    ip_hash = _ip_hash(ip) if ip else ""

    cache_key = f"subscribe:rl:{ip_hash or 'unknown'}"
    attempts = cache.get(cache_key, 0)
    if attempts >= RATE_LIMIT_MAX:
        return JsonResponse({"ok": False, "message": RATE_LIMIT_MSG}, status=429)
    cache.set(cache_key, attempts + 1, RATE_LIMIT_WINDOW)

    if honeypot:
        return JsonResponse({"ok": True, "message": SUCCESS_MSG})

    validator = EmailValidator()
    try:
        validator(email_raw)
    except Exception:
        return JsonResponse({"ok": False, "message": INVALID_MSG}, status=400)

    email = email_raw.strip().lower()

    if Subscriber.objects.filter(email__iexact=email).exists():
        return JsonResponse({"ok": True, "message": SUCCESS_MSG})

    Subscriber.objects.create(
        email=email,
        ip_hash=ip_hash,
    )
    return JsonResponse({"ok": True, "message": SUCCESS_MSG})


def robots_txt(request):
    site = settings.SITE_URL.rstrip("/")
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {site}/sitemap.xml\n"
    )
    return HttpResponse(body, content_type="text/plain")


def sitemap_xml(request):
    site = settings.SITE_URL.rstrip("/")
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        "  <url>\n"
        f"    <loc>{site}/</loc>\n"
        "  </url>\n"
        "  <url>\n"
        f"    <loc>{site}/privacy/</loc>\n"
        "  </url>\n"
        "</urlset>\n"
    )
    return HttpResponse(body, content_type="application/xml")
