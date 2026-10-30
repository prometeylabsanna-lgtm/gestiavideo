from axes.apps import AppConfig as AxesAppConfig
from django.utils.translation import gettext_lazy as _


class AxesConfig(AxesAppConfig):
    """Ukrainian label for django-axes in admin app list / Unfold sidebar."""

    verbose_name = _("Axes")
