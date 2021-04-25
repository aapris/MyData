"""
Logbook app contains a timeline of "all possible" stuff.

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
- strength in scale 0-10

Pain and other physical sensations
- location (in body, if local)
- intensity (0-10)
- type (sharp, incisive, dizzy)

"""
import os

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.gis.db import models
from django.contrib.postgres.fields import ArrayField
from django.db.models.signals import pre_delete
from django.dispatch.dispatcher import receiver

import logbook.utils


class Profile(models.Model):
    user = models.OneToOneField(User, primary_key=True, on_delete=models.CASCADE)
    timezone = models.CharField(max_length=100, default=settings.TIME_ZONE)


class Attachment(models.Model):
    message = models.ForeignKey("Message", on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="attachments/%Y/%m/%d/")
    mimetype = models.CharField(max_length=256)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{} {}".format(self.file.name, self.mimetype)


@receiver(pre_delete, sender=Attachment)
def attachment_delete(sender, instance, **kwargs):
    """Delete associated file from file system"""
    # Pass false so FileField doesn't save the model.
    if instance.file:
        if os.path.isfile(instance.file.path):
            instance.file.delete(False)


class Keyword(models.Model):
    words = ArrayField(models.CharField(max_length=32, unique=True))
    type = models.CharField(max_length=32, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{} ({})".format(self.type, self.words)


class Record(models.Model):
    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE)
    message = models.OneToOneField("Message", blank=True, null=True, on_delete=models.SET_NULL, related_name="record")
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE)
    type = models.CharField(max_length=256, blank=True)  # One of Keyword.words
    name = models.CharField(max_length=256)
    description = models.CharField(blank=True, max_length=256)
    status = models.IntegerField(default=1)
    time = models.DateTimeField(db_index=True)

    # Keyword / activity type related fields. May be null, if field is not appropriate
    intensity = models.FloatField(blank=True, null=True)  # Physical or mental sensation, e.g. emotion, pain, cold, hot
    abv = models.FloatField(blank=True, null=True)  # Alcohol by volume %, e.g. 4.5, 13.5, 40.0
    volume = models.FloatField(blank=True, null=True)  # amount in litres
    quantity = models.FloatField(blank=True, null=True)  # amount in kilograms
    rating = models.FloatField(blank=True, null=True)  # rating, range e.g. 0-5 or 0-10

    # For convenience, lat and lon in numeric form too
    lat = models.FloatField(null=True, editable=False)  # degrees (°) -90.0 - 90.0
    lon = models.FloatField(null=True, editable=False)  # degrees (°) -180.0 - 180.0
    geometry = models.PointField(geography=True, null=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{}: {} {}".format(self.keyword.type, self.name, self.time)


class Message(models.Model):
    user = models.ForeignKey(User, db_index=True, on_delete=models.CASCADE)
    status = models.IntegerField(default=1)
    time = models.DateTimeField(db_index=True)
    text = models.CharField(max_length=1000)
    source = models.CharField(max_length=32, blank=True)
    source_id = models.CharField(max_length=64, blank=True, unique=True)  # identifier in another system
    json = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def update_record(self) -> Record:
        self.record = record_from_message(self)
        if hasattr(self, "record"):
            return self.record

    def __str__(self):
        return "({}) {} ({})".format(self.id, self.text[:30], self.source)


def record_from_message(message: Message) -> Record:
    """
    Parse Message.text and create a Record from the data.
    If there is no valid Keyword available, return None

    :param message: Message object
    :return: Record object
    """
    words = message.text.split()
    if words:  # E.g. location has empty text
        kw_str = logbook.utils.sanitize_keyword(words.pop(0))
        kws = Keyword.objects.filter(words__contains=[kw_str])
        if kws.count() == 1:
            if len(words) > 0:
                vol = logbook.utils.parse_volume(words)
                percentage = logbook.utils.parse_percentage(words)
                weight = logbook.utils.parse_weight(words)
                intensity = logbook.utils.parse_float(words)
                rating = logbook.utils.parse_star_rating(words)
                timezone = message.user.profile.timezone if hasattr(message.user, "profile") else settings.TIME_ZONE
                timestamp = logbook.utils.pick_time(words, timezone=timezone, timestamp=message.time)
                description = " ".join(words)
                if not hasattr(message, "record"):
                    r = Record(message=message)
                else:
                    r = message.record
                r.keyword = kws[0]
                r.type = r.keyword.type
                r.user = message.user
                r.name = kw_str
                r.description = description
                r.volume = vol
                r.abv = percentage
                r.quantity = weight
                r.intensity = intensity
                r.rating = rating
                r.time = timestamp
                r.save()
                return r
