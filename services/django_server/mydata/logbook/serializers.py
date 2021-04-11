from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.relations import PrimaryKeyRelatedField

from logbook.models import Message, Keyword, Attachment


class KeywordSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Keyword
        fields = [
            "id",
            "words",
            "type",
        ]


class AttachmentSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Attachment
        fields = [
            "id",
            "file",
            "url",
        ]


class MessageSerializer(serializers.HyperlinkedModelSerializer):
    #    files = FileSerializer()
    #    files = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    attachments = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name="attachment-detail")

    user = PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Message
        fields = [
            "id",
            "user",
            "attachments",
            "status",
            "time",
            "text",
            "source",
            "created_at",
            "updated_at",
        ]
