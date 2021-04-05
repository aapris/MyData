from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.relations import PrimaryKeyRelatedField

from logbook.models import Alcohol, Drink, Nutrition, Activity, Drug, Message, Keyword, RawFile


class KeywordSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Keyword
        fields = [
            "id",
            "words",
            "model",
        ]


class FileSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = RawFile
        fields = [
            "id",
            "file",
            "url",
        ]


class MessageSerializer(serializers.HyperlinkedModelSerializer):
    #    files = FileSerializer()
    #    files = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    files = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='rawfile-detail')

    user = PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Message
        fields = [
            "id",
            "user",
            "files",
            "status",
            "time",
            "text",
            "source",
            "created_at",
            "updated_at",
        ]
