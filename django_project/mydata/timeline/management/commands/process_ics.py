import logging
import os
from typing import Optional

import requests
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from icalendar import Calendar

from timeline.models import Event, Source


def read_url(url: str) -> str:
    """
    Return url contents.
    :param url: URL for request
    :return: return response content string
    """
    cal_data = requests.get(url).text
    return cal_data


def read_file(path: str) -> str:
    """
    Return file contents.
    :param path: path to file
    :return: return file content string
    """
    with open(path, "rt") as f:
        cal_data = f.read()
    return cal_data


def read_cal(uri: str) -> Optional[Calendar]:
    """
    Read .ics file from uri and return a Calendar object.
    :param uri: URL or path to ical file
    :return: iCalendar object
    """
    if os.path.isfile(uri):
        with open(uri, "rt") as f:
            cal = Calendar.from_ical(f.read())
    elif uri.startswith("http"):
        cal = Calendar.from_ical(requests.get(uri).text)
    else:
        return None
    return cal


def process_cal(cal: Calendar, user: User, source: str, limit=0) -> None:
    """
    Loop all timeline events and save a new or update an existing Event object.
    """
    i = 0
    for ev in cal.walk("vevent"):
        serialized = ev.to_ical().decode("utf-8").replace("\r\n", "\n").replace(r"\,", ",").strip()
        uid = ev.get("uid")
        to_save = False
        try:
            e = Event.objects.get(uid=uid, user=user, source=source)
            if e.serialized != serialized:
                e.serialized = serialized
                e.parse_serialized()
                to_save = True
        except Event.DoesNotExist:
            e = Event(uid=uid, user=user, source=source, serialized=serialized)
            e.parse_serialized()
            to_save = True
        # if geo:
        #     try:
        #         coords = [float(x) for x in geo.split(';')]
        #         e.geo = Point(coords[1], coords[0])
        #     except Exception:
        #         raise
        #     print(geo, coords, e.geo)
        # if to_save:
        #     e.serialized = ev.to_ical().decode("utf-8").replace('\r\n', '\n').strip()
        #     e.save()
        print(to_save, e.uid, e.summary, e.starttime, e.endtime, e.location.encode("utf8") if e.location else None)
        i += 1
        if 0 < limit <= i:
            return


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", action="store", dest="limit", type=int, default=0, help="Limit the number of events to handle"
        )
        parser.add_argument(
            "--log", default="ERROR", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Log level"
        )
        parser.add_argument("--uri", action="store", dest="uri", required=True, help="URI for ics")
        parser.add_argument("--source", action="store", dest="source", required=True, help="Source for ics")
        parser.add_argument("--username", action="store", dest="username", required=True, help="username")

    def handle(self, *args, **options):
        logging.basicConfig(format="%(asctime)s %(levelname)-8s %(message)s", level=getattr(logging, options["log"]))
        uri = options["uri"]
        limit = options["limit"]
        source = options["source"]
        src, created = Source.objects.get_or_create(slug=source)
        if uri is None:
            print("Nothing to do. You must give at least --uri parameter")
            exit()
        cal = read_cal(uri)
        user = User.objects.get(username=options["username"])
        process_cal(cal, user, src, limit)
