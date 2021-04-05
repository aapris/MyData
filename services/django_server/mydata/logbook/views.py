from rest_framework import filters
from rest_framework import viewsets

from logbook.models import Alcohol, Drink, Nutrition, Activity, Drug, Message, Keyword, RawFile
from logbook.serializers import MessageSerializer, KeywordSerializer, FileSerializer


class FileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Files to be viewed.

    """
    queryset = RawFile.objects.all().order_by("-created_at")
    serializer_class = FileSerializer


class MessageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Messages to be viewed.

    **Search fields:** summary, description
    """

    queryset = Message.objects.all().order_by("-time")
    serializer_class = MessageSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["text"]


class KeywordViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Keywords to be viewed.

    **Search fields:** words, model
    """

    queryset = Keyword.objects.all().order_by("model")
    serializer_class = KeywordSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["words", "model"]
