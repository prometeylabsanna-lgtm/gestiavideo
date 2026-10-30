from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from django.views.generic import RedirectView

from subscribers.views import IndexView, robots_txt, sitemap_xml

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("", IndexView.as_view(), name="index"),
    path("", include("subscribers.urls")),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap_xml, name="sitemap_xml"),
    path(
        "favicon.ico",
        RedirectView.as_view(
            url=f"{settings.STATIC_URL}assets/img/favicon.ico",
            permanent=False,
        ),
        name="favicon",
    ),
]


def healthz(_request):
    return HttpResponse("ok", content_type="text/plain")


urlpatterns.append(path("healthz", healthz, name="healthz"))
