"""
Timeline app contains mostly data from timeline type events.

BEGIN:VEVENT
DTSTART:20190825T090000Z
DTEND:20190825T100000Z
DTSTAMP:20201226T004453Z
UID:1AA41EC0-9A68-4458-8E53-2B50881BC2AE
CREATED:20190825T141748Z
DESCRIPTION:
LAST-MODIFIED:20190825T141827Z
LOCATION:Kauppatori\nPohjoisesplanadi 7\, 00170 Helsinki\, Suomi
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:Kauppatori - Isosaari vene
TRANSP:OPAQUE
X-APPLE-STRUCTURED-LOCATION;VALUE=URI;X-ADDRESS="Pohjoisesplanadi 7, 00170
 Helsinki, Suomi";X-APPLE-MAPKIT-HANDLE=CAESwwEIrk0Q0s+X9rvT+YkpGhIJ5L7VOnEV
 TkARxEVJo130OEAiZwoFU3VvbWkSAkZJGgdVdXNpbWFhMghIZWxzaW5raToFMDAxNzBSEFBvaGp
 vaXNlc3BsYW5hZGlaATdiElBvaGpvaXNlc3BsYW5hZGkgN4oBCEhlbHNpbmtpigELS3J1dW51bm
 hha2EqCkthdXBwYXRvcmkyElBvaGpvaXNlc3BsYW5hZGkgNzIOMDAxNzAgSGVsc2lua2kyBVN1b
 21pOC0=;X-APPLE-RADIUS=144.4846349409346;X-APPLE-REFERENCEFRAME=1;X-TITLE=K
 auppatori:geo:60.167518,24.954554
BEGIN:VALARM
ACTION:NONE
TRIGGER;VALUE=DATE-TIME:19760401T005545Z
END:VALARM
END:VEVENT

Foursquare has keys
[u'timestamp', u'uid', u'url', u'summary', u'location',
 u'endtime', u'starttime', u'geo', u'description']

BEGIN:VEVENT
DTSTAMP:20171127T010000Z
DTSTART:20171126T141337Z
DTEND:20171126T141337Z
UID:xxxxxxxxxxxxxxxxxxxxxxxx@foursquare.com
URL:https://foursquare.com/someuser/checkin/xxxxxxxxxxxxxxxxxxxxx
GEO:60.165847561712305;24.965931299517525
SUMMARY:@ Katajanokka / Skatudden
DESCRIPTION:@ Katajanokka / Skatudden
LOCATION:Katajanokka / Skatudden
END:VEVENT

Google timeline export:
[u'status', u'attendee', u'uid', u'sequence', u'recurrence-id',
 u'x-apple-travel-duration', u'transp', u'timestamp', u'last-modified',
 u'rrule', u'x-apple-needs-reply', u'endtime', u'starttime', u'class',
 u'organizer', u'categories', u'description', u'valarm', u'created',
 u'url', u'summary', u'x-apple-structured-location', u'location',
 u'x-google-hangout', u'exdate']
BEGIN:VEVENT
DTSTART:20171126T140000Z
DTEND:20171126T150000Z
DTSTAMP:20171126T004514Z
UID:203CDCC5-4077-8267-A284-74AD4BF60406
CREATED:20171120T155121Z
DESCRIPTION:Sample note
LAST-MODIFIED:20171120T155616Z
LOCATION:Viking Line - Day Cruises\nMastokatu 1\, 00160 Helsinki\, Finland
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:Harbour
TRANSP:OPAQUE
X-APPLE-STRUCTURED-LOCATION;VALUE=URI;X-APPLE-MAPKIT-HANDLE=CAESzwEIrk0Q76e
 xzaW5raToFMDAxNjBCC0thdGFqYW5va2thUglNYXN0b2thdHVaATFiC01hc3Rva2F0dSAxcgtLY
 rssbw14/sARoSCY7SDyQVFU5AEWY5cFTw9zhAImoKB0ZpbmxhbmQSAkZJGgdVdXNpbWFhMghIZW
 XRhamFub2trYYoBC0thdGFqYW5va2thKhlWaWtpbmcgTGluZSAtIERheSBDcnVpc2VzMgtNYXN0
 b2thdHUgMTIOMDAxNjAgSGVsc2lua2kyB0ZpbmxhbmQ=;X-APPLE-RADIUS=99.826449404325
 42;X-TITLE="Viking Line - Day Cruises\nMastokatu 1, 00160 Helsinki, Finland
 ":geo:60.164708,24.968511
X-APPLE-TRAVEL-ADVISORY-BEHAVIOR:AUTOMATIC
END:VEVENT
"""
from typing import Optional

import icalendar
from django.contrib.auth.models import User
from django.contrib.gis.db import models

from timeline.utils import vevent_to_object


class Source(models.Model):
    name = models.CharField(max_length=512, blank=True, editable=True)
    slug = models.SlugField(max_length=512, editable=True)
    # Django fields
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{} ({})".format(self.name, self.slug)


class Event(models.Model):
    """
    Imported ical events are stored here.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=40,
        default="UNPROCESSED",
        choices=(
            ("UNPROCESSED", "Unprocessed"),
            ("PROCESSED", "Processed"),
            ("DUPLICATE", "Duplicate"),
            ("DELETED", "Deleted"),
        ),
    )
    # VEVENT fields
    source = models.ForeignKey("Source", on_delete=models.CASCADE)
    uid = models.CharField(max_length=1000, unique=True, db_index=True, editable=False)
    summary = models.CharField(max_length=512, blank=True, editable=True)
    description = models.TextField(blank=True, editable=True)
    url = models.TextField(blank=True, editable=False)
    location = models.CharField(max_length=512, blank=True, editable=True)
    starttime = models.DateTimeField()  # DTSTART
    endtime = models.DateTimeField(blank=True, null=True)  # DTEND
    timestamp = models.DateTimeField(blank=True, null=True)  # DTSTAMP
    geo = models.PointField(geography=True, blank=True, null=True)
    created = models.DateTimeField(blank=True, null=True)
    last_modified = models.DateTimeField(blank=True, null=True)
    serialized = models.TextField(blank=True)
    # Django fields
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def parse_serialized(self) -> Optional[dict]:
        """
        (Re)parse VEVENT data using icalendar and save the values into object's fields
        :return: None or a dict containing changed fields
        """
        if self.serialized == "":  # Do not parse empty value, but return None
            return None
        # This raises ValueError (as intended) if value is not a valid VEVENT
        ev_data = vevent_to_object(icalendar.Calendar.from_ical(self.serialized))
        changed_fields = dict()  # Contains all changed fields and their original value
        for key, val in ev_data.items():
            if getattr(self, key) != val:
                changed_fields[key] = getattr(self, key)
                setattr(self, key, val)
        if changed_fields:
            if self.pk is None:
                self.save()
            else:
                # Using update_fields may be a performance benefit,
                # check PostgreSQL HOT updates and table fillfactor
                self.save(update_fields=ev_data.keys())
        return changed_fields

    def __str__(self):
        return "{}: {}".format(self.starttime, self.summary)
