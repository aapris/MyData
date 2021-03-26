# from rest_framework_gis.serializers import GeoFeatureModelSerializer
# from django.contrib.gis.db.models import GeometryField, LineStringField
from rest_framework import serializers

# from rest_framework.exceptions import ValidationError

from timeline.models import Source, Event


class EventSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Event
        fields = [
            "id",
            "source",
            "uid",
            "summary",
            "description",
            "url",
            "location",
            "starttime",
            "endtime",
            "timestamp",
            "geo",
            "created",
            "last_modified",
            "created_at",
            "updated_at",
        ]


class SourceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Source
        fields = ["id", "name", "slug", "created_at", "updated_at"]


# class TracksegSerializer(serializers.HyperlinkedModelSerializer):
#     class Meta:
#         model = Trackseg
#         fields = ["id", "length", "trackpoint_cnt", "starttime", "endtime", "created_at", "geometry"]
#
#     def to_representation(self, instance):
#         """Simplify original LineString to save resources."""
#         request = self.context.get("request")
#         try:
#             tolerance = float(request.GET.get("simplify_tolerance", 10.0))
#         except ValueError as err:
#             raise ValidationError(detail=f"Invalid 'simplify_tolerance' value: {err}")
#         if tolerance >= 0:
#             instance.geometry = simplify(instance.geometry, tolerance=tolerance)
#         ret = super().to_representation(instance)
#         return ret
