from django.contrib import admin

from timeline.models import Source, Event

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S %z"


def starttime_iso(obj):
    return obj.starttime.strftime(TIMESTAMP_FORMAT)


starttime_iso.admin_order_field = "starttime"
starttime_iso.short_description = "Start time"


class SourceAdmin(admin.ModelAdmin):
    pass


admin.site.register(Source, SourceAdmin)


class EventAdmin(admin.ModelAdmin):
    list_display = ["summary", starttime_iso]
    search_fields = ["summary", "description", "location", "serialized"]
    readonly_fields = [
        "user", "source", "status", "uid", "summary", "description", "url", "starttime", "endtime",
        "timestamp", "geo", "created", "last_modified", "location", "serialized", "created_at", "updated_at"
    ]


admin.site.register(Event, EventAdmin)
