from django.contrib import admin

from logbook.models import Keyword, Message, Attachment, Record


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ["words", "type"]
    search_fields = ["words", "type"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["text", "get_attachment", "time"]
    search_fields = ["text"]
    readonly_fields = ["time"]

    def get_attachment(self, obj):
        attachments = obj.attachments.all()
        if attachments:
            return attachments[0].file.name

    get_attachment.short_description = "Attachment"


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    list_display = ["type", "name", "description", "quantity", "intensity", "abv", "volume", "time"]
    search_fields = ["type", "name", "description"]
    readonly_fields = ["message"]


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ["file"]
