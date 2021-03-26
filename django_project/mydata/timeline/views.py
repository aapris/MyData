from rest_framework import filters
from rest_framework import viewsets

from timeline.models import Source, Event
from timeline.serializers import SourceSerializer, EventSerializer


class SourceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Sources to be viewed.
    """

    queryset = Source.objects.all().order_by("slug")
    serializer_class = SourceSerializer


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Events to be viewed.

    **Search fields:** summary, description
    """

    queryset = Event.objects.all().order_by("starttime")
    serializer_class = EventSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["summary", "description"]
