"""
Justnow app contains a timeline of "all possible" stuff.

All objects have these fields
- time of event
- created at
- location (coordinates + accuracy)

Consumed things
- food (name, amount)
- drinks (tea, coffee, soft drinks)
- alcohol (volume * ABV), type
- medicines (weight, name)
- drugs

Emotional state and other mental sensations
- mood (happiness, sorrow, zeal, anger, anxiety)
- strength in scale 0-100

Pain and other physical sensations
- location (in body, if local)
- intensity (0-100)
- type (sharp, incisive, dizzy)

"""
import os

from django.contrib.auth.models import User
from django.contrib.gis.db import models
from django.contrib.postgres.fields import ArrayField
from django.db.models.signals import pre_delete
from django.dispatch.dispatcher import receiver


class Message(models.Model):
    user = models.ForeignKey(User, db_index=True, on_delete=models.CASCADE)
    status = models.IntegerField(default=1)
    time = models.DateTimeField(db_index=True)
    text = models.CharField(max_length=1000)
    source = models.CharField(max_length=32, blank=True)
    json = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "({}) {} ({})".format(self.id, self.text[:30], self.source)


# TODO: rename to something else
class RawFile(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to="files/%Y/%m/%d/")
    mimetype = models.CharField(max_length=256)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{} {}".format(self.file.name, self.mimetype)


@receiver(pre_delete, sender=RawFile)
def rawfile_delete(sender, instance, **kwargs):
    """Delete associated file from file system"""
    # Pass false so FileField doesn't save the model.
    if instance.file:
        if os.path.isfile(instance.file.path):
            instance.file.delete(False)


class BaseLogbookModel(models.Model):
    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE)
    message = models.ForeignKey(Message, blank=True, null=True, on_delete=models.SET_NULL)
    keyword = models.CharField(max_length=32, blank=True)
    type = models.CharField(max_length=256, blank=True)  # One of Keyword.words
    name = models.CharField(max_length=256)
    status = models.IntegerField(default=1)
    time = models.DateTimeField(db_index=True)
    # For convenience, lat and lon in numeric form too
    lat = models.FloatField(null=True, editable=False)  # degrees (°) -90.0 - 90.0
    lon = models.FloatField(null=True, editable=False)  # degrees (°) -180.0 - 180.0
    geometry = models.PointField(geography=True, null=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return "{}: {} {}".format(self.keyword, self.name, self.time)


class Sensation(BaseLogbookModel):
    """Physical or mental sensation, e.g. emotion, pain, cold, hot"""

    intensity = models.FloatField(blank=True, null=True)


class Activity(BaseLogbookModel):
    """Physical activity (body function), which is not measured by activity trackers.
    E.g. poo, pee, fart, puke"""

    description = models.CharField(blank=True, max_length=256)


class Nutrition(BaseLogbookModel):
    """Food and drinks (without alcohol)"""

    description = models.CharField(max_length=256)
    quantity = models.FloatField(blank=True, null=True)  # kg


class Alcohol(BaseLogbookModel):
    """Alcohol, e.g. Urquell, beer, 4.4, 0.5"""

    abv = models.FloatField(blank=True, null=True)  # Alcohol by volume %, e.g. 4.5, 13.5, 40.0
    volume = models.FloatField(blank=True, null=True)  # amount in litres


class Drink(BaseLogbookModel):
    """A drink without alcohol, e.g. water, coffee, tea, soft drink, any other beverage"""

    volume = models.FloatField(blank=True, null=True)  # amount in litres


class Drug(BaseLogbookModel):
    """Medicines, drugs, dopes, narcotics"""

    quantity = models.FloatField(blank=True, null=True)  # mg


class Keyword(models.Model):
    words = ArrayField(models.CharField(max_length=32, unique=True))
    model = models.CharField(max_length=32, unique=True)

    def __str__(self):
        return "{} ({})".format(self.model, self.words)
