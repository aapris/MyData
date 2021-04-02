from django.contrib import admin

from logbook.models import Alcohol, Drug, Drink, Sensation, Nutrition
from logbook.models import Message, Keyword


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ["words", "model"]
    search_fields = ["words", "model"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["text", "get_file", "time"]
    search_fields = [
        "text",
    ]
    readonly_fields = [
        "time",
    ]

    def get_file(self, obj):
        files = obj.file.all()
        if files:
            return files[0].file.name

    get_file.short_description = "File"


@admin.register(Alcohol)
class AlcoholAdmin(admin.ModelAdmin):
    list_display = ["type", "name", "abv", "volume", "time"]
    search_fields = ["type", "name"]
    readonly_fields = ["message"]


@admin.register(Sensation)
class SensationAdmin(admin.ModelAdmin):
    list_display = ["type", "name", "intensity", "time"]
    search_fields = ["type", "name"]
    readonly_fields = ["message"]


@admin.register(Nutrition)
class NutritionAdmin(admin.ModelAdmin):
    list_display = ["type", "name", "quantity", "time"]
    search_fields = ["type", "name"]
    readonly_fields = ["message"]


@admin.register(Drug)
class DrugAdmin(admin.ModelAdmin):
    list_display = ["type", "name", "quantity", "time"]
    search_fields = ["type", "name", "quantity"]
    readonly_fields = ["message"]


@admin.register(Drink)
class DrinkAdmin(admin.ModelAdmin):
    list_display = ["type", "name", "volume", "time"]
    search_fields = ["type", "name"]
    readonly_fields = ["message"]
