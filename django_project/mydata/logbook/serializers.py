from rest_framework import serializers

from logbook.models import Alcohol, Drink, Nutrition, Activity, Drug, Message, Keyword


class KeywordSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Keyword
        fields = [
            "id",
            "words",
            "model",
        ]


class MessageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Message
        fields = [
            "id",
            "files",
            "status",
            "time",
            "text",
            "source",
            "created_at",
            "updated_at",
        ]
