import re

import icalendar
from django.contrib.gis.geos import Point

# A dict to map VEVENT fields to model.Event's fields
keys_map = {
    "DTSTART": "starttime",
    "DTEND": "endtime",
    "DTSTAMP": "timestamp",
    "LAST-MODIFIED": "last_modified",
    "CREATED": "created",
    "UID": "uid",
    "DESCRIPTION": "description",
    "SUMMARY": "summary",
}


def vevent_to_object(vevent_data) -> dict:
    """
    icalendar.Calendar.from_ical(str) returns funny datatypes so
    this function converts them to datetimes and strings.
    :param vevent_data:
    :return: event data as a dict
    """
    ev_data = {}
    for key, field in keys_map.items():
        val = vevent_data.get(key)
        if isinstance(val, icalendar.prop.vDDDTypes):
            # FIXME: all-day events have unaware date here, not datetime
            # TODO: determine how to handle this
            val = val.dt
        elif isinstance(val, icalendar.prop.vText):
            val = str(val)
        if val:
            ev_data[field] = val
    apple_location = vevent_data.get("X-APPLE-STRUCTURED-LOCATION", "")
    m = re.match(r"geo:([-\d.]+),([-\d.]+)", apple_location)
    if m:
        ev_data["geo"] = Point(float(m[2]), float(m[1]))
    return ev_data
