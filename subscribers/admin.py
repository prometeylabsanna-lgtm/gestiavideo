import csv

from django.contrib import admin, messages
from django.http import HttpResponse
from unfold.admin import ModelAdmin

from .models import Subscriber


@admin.register(Subscriber)
class SubscriberAdmin(ModelAdmin):
    list_display = ("email", "created_at", "source", "lang")
    search_fields = ("email",)
    list_filter = ("created_at", "source")
    readonly_fields = ("created_at", "ip_hash")
    date_hierarchy = "created_at"
    actions = ("export_csv",)
    ordering = ("-created_at",)

    def changelist_view(self, request, extra_context=None):
        total = Subscriber.objects.count()
        messages.info(request, f"Всього: {total}")
        return super().changelist_view(request, extra_context=extra_context)

    @admin.action(description="Експортувати в CSV")
    def export_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="subscribers.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow(["email", "created_at", "source", "lang"])
        for row in queryset.order_by("created_at"):
            writer.writerow(
                [
                    row.email,
                    row.created_at.isoformat(),
                    row.source,
                    row.lang,
                ]
            )
        return response
