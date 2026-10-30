from django.conf import settings


def site(request):
    return {
        "SITE_URL": getattr(settings, "SITE_URL", "https://gestia-home.com").rstrip("/"),
    }
