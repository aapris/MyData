from django.contrib.gis.geos import Polygon
from rest_framework import filters
from rest_framework import viewsets
from rest_framework.exceptions import ParseError

from track.models import Trackfile, Trackpoint, Trackseg
from track.serializers import TrackfileSerializer, TrackpointSerializer, TracksegSerializer


class TrackpointViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Trackpoints to be viewed.
    """

    queryset = Trackpoint.objects.order_by("time")
    serializer_class = TrackpointSerializer

    def get_queryset(self):
        """
        Bounding box filter is in standard format
        bbox = left,bottom,right,top
        bbox = min Longitude , min Latitude , max Longitude , max Latitude
        """
        queryset = Trackpoint.objects.order_by("time")
        bbox = self.request.query_params.get("bbox")
        if bbox:
            points = bbox.split(",")
            if len(points) == 4:
                try:
                    points = [float(p) for p in points]
                    poly = Polygon.from_bbox(points)
                except ValueError:
                    raise ParseError(
                        "bbox must be in format 'min Lon, min Lat, max Lon, max Lat' where all values are floats"
                    )
            else:
                raise ParseError("bbox must be in format 'min Lon, min Lat, max Lon, max Lat'")
            queryset = queryset.filter(geometry__coveredby=poly)
        return queryset


class TracksegViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Tracksegs to be viewed.

    * LineString is simplified with default tolerance 10.0.
      Add parameter `simplify_tolerance=n` (where n>0) to get more or less points in it.
    * To get all points in `geometry` LineString field, add parameter `simplify_tolerance=-1`
    """

    queryset = Trackseg.objects.all().order_by("starttime")
    serializer_class = TracksegSerializer


class TrackfileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Trackfiles to be viewed.
    """

    queryset = Trackfile.objects.all().order_by("starttime")
    serializer_class = TrackfileSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["filename"]
