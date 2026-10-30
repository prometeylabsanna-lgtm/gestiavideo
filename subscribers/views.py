import hashlib
import json

from django.conf import settings
from django.core.cache import cache
from django.core.validators import EmailValidator
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
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

FORM_STATUS_BY_QUERY = {
    "subscribed": (SUCCESS_MSG, False),
    "invalid": (INVALID_MSG, True),
    "rate": (RATE_LIMIT_MSG, True),
}


@method_decorator(ensure_csrf_cookie, name="dispatch")
class IndexView(TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET
        form_status = ""
        form_status_error = False
        if "subscribed" in params and params.get("subscribed") == "1":
            form_status, form_status_error = FORM_STATUS_BY_QUERY["subscribed"]
        elif params.get("error") == "invalid":
            form_status, form_status_error = FORM_STATUS_BY_QUERY["invalid"]
        elif params.get("error") == "rate":
            form_status, form_status_error = FORM_STATUS_BY_QUERY["rate"]
        context["form_status"] = form_status
        context["form_status_error"] = form_status_error
        return context


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


def _wants_json(request):
    content_type = request.META.get("CONTENT_TYPE", "")
    if "application/json" in content_type:
        return True
    accept = request.META.get("HTTP_ACCEPT", "")
    return "application/json" in accept and "text/html" not in accept


def _subscribe_response(request, *, ok, message, status=200, redirect_to=None):
    if _wants_json(request):
        return JsonResponse({"ok": ok, "message": message}, status=status)
    response = HttpResponseRedirect(redirect_to or "/")
    response.status_code = 303
    return response


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
        return _subscribe_response(
            request,
            ok=False,
            message=RATE_LIMIT_MSG,
            status=429,
            redirect_to="/?error=rate",
        )
    cache.set(cache_key, attempts + 1, RATE_LIMIT_WINDOW)

    if honeypot:
        return _subscribe_response(
            request,
            ok=True,
            message=SUCCESS_MSG,
            redirect_to="/?subscribed=1",
        )

    validator = EmailValidator()
    try:
        validator(email_raw)
    except Exception:
        return _subscribe_response(
            request,
            ok=False,
            message=INVALID_MSG,
            status=400,
            redirect_to="/?error=invalid",
        )

    email = email_raw.strip().lower()

    if Subscriber.objects.filter(email__iexact=email).exists():
        return _subscribe_response(
            request,
            ok=True,
            message=SUCCESS_MSG,
            redirect_to="/?subscribed=1",
        )

    Subscriber.objects.create(
        email=email,
        ip_hash=ip_hash,
    )
    return _subscribe_response(
        request,
        ok=True,
        message=SUCCESS_MSG,
        redirect_to="/?subscribed=1",
    )


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


def site_webmanifest(request):
    static = settings.STATIC_URL
    if not static.endswith("/"):
        static = f"{static}/"
    payload = {
        "name": "Gestia Home",
        "short_name": "Gestia Home",
        "start_url": "/",
        "display": "browser",
        "lang": "uk",
        "theme_color": "#251008",
        "background_color": "#251008",
        "icons": [
            {
                "src": f"{static}assets/img/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
            },
            {
                "src": f"{static}assets/img/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
            },
        ],
    }
    return HttpResponse(
        json.dumps(payload, ensure_ascii=False, indent=2),
        content_type="application/manifest+json",
    )
