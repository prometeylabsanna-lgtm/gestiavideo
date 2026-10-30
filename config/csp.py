"""Content-Security-Policy middleware: strict for public, relaxed for admin."""

from django.conf import settings

CSP_HEADER = "Content-Security-Policy"

# Matches the previous nginx public policy exactly.
CSP_STRICT = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "font-src 'self'; "
    "img-src 'self' data:; "
    "media-src 'self'; "
    "connect-src 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "object-src 'none'"
)

# Unfold admin needs inline <style> and Alpine.js (unsafe-inline / unsafe-eval).
CSP_ADMIN = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "object-src 'none'"
)


def _admin_path_prefix():
    return "/" + settings.ADMIN_URL.lstrip("/")


class ContentSecurityPolicyMiddleware:
    """Set CSP on every response unless a view already set the header."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if CSP_HEADER in response:
            return response
        if request.path.startswith(_admin_path_prefix()):
            response[CSP_HEADER] = CSP_ADMIN
        else:
            response[CSP_HEADER] = CSP_STRICT
        return response
