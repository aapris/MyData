from django.contrib.gis import admin

from track.models import Tracksource, Trackfile, Trackseg, Trackpoint

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S %z"


def starttime_iso(obj):
    return obj.starttime.strftime(TIMESTAMP_FORMAT)


starttime_iso.admin_order_field = "starttime"
starttime_iso.short_description = "Start time"


def endtime_iso(obj):
    return obj.endtime.strftime(TIMESTAMP_FORMAT)


endtime_iso.admin_order_field = "endtime"
endtime_iso.short_description = "Start time"


class TracksourceAdmin(admin.ModelAdmin):
    pass


class TrackfileAdmin(admin.OSMGeoAdmin):
    list_display = ["filename", "filesize", starttime_iso, endtime_iso]
    search_fields = ["filename", "starttime", "endtime"]
    readonly_fields = ["filename", "filesize", "trackpoint_cnt", "starttime", "endtime"]


class TracksegAdmin(admin.OSMGeoAdmin):
    list_display = [starttime_iso, endtime_iso, "trackpoint_cnt", "length_km"]


class TrackpointAdmin(admin.OSMGeoAdmin):
    list_display = ["pk", "lat", "lon", "time"]


admin.site.register(Tracksource, TracksourceAdmin)
admin.site.register(Trackfile, TrackfileAdmin)
admin.site.register(Trackseg, TracksegAdmin)
admin.site.register(Trackpoint, TrackpointAdmin)
