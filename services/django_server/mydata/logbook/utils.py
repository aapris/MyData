import datetime
import re
from typing import Optional, Pattern

import pytz

vol_units = {"l": 1, "dl": 0.1, "cl": 0.01, "ml": 0.001}
weight_units = {"kg": 1, "g": 0.001, "mg": 0.000001}
kw_re: Pattern[str] = re.compile(r"[^\w]")
hhmm_re: Pattern[str] = re.compile(r"([-+])?(\d+):(\d\d)")
minute_re: Pattern[str] = re.compile(r"([-+])(\d+)m")
float_re: Pattern[str] = re.compile(r"(\d+\.\d+)")
vol_re: Pattern[str] = re.compile(r"(\d+\.?\d*)({})".format("|".join(vol_units.keys())))
weight_re: Pattern[str] = re.compile(r"(\d+\.?\d*)({})".format("|".join(weight_units.keys())))
percentage_re: Pattern[str] = re.compile(r"(\d+\.?\d*)%")


def sanitize_keyword(s: str) -> str:
    return kw_re.sub('', s).lower()


def parse_single_match(words: list, compiled_re: re.Pattern) -> float:
    """
    Loop through words and try to match them to compiled_re.
    Return match as a float.
    Note: current word is removed from original list.
    :param words: list of words
    :param compiled_re:
    :return: float volume
    """
    for i in range(len(words)):
        w = words[i].replace(",", ".")
        m = compiled_re.findall(w)
        if m:
            val = float(m[0])
            words.pop(i)
            return val


def parse_dup_match(words: list, compiled_re: re.Pattern, units: dict) -> float:
    """
    Loop through words and return a float, if a volume string (1dl, 0.5l etc) is found.
    Note: current word is removed from original list.
    :param words: list of words
    :param compiled_re:
    :param units:
    :return: float volume
    """
    for i in range(len(words)):
        w = words[i].replace(",", ".")
        m = compiled_re.findall(w)
        if m:
            val = float(m[0][0]) * units[m[0][1]]
            words.pop(i)
            return val


def parse_volume(words: list) -> float:
    return parse_dup_match(words, vol_re, vol_units)


def parse_weight(words: list) -> float:
    """
    Loop through words and return a float, if a weight string (1kg, 400g etc) is found.
    """
    return parse_dup_match(words, weight_re, weight_units)


def parse_percentage(words: list) -> float:
    """
    Loop through words and return a float, if a % string (2%, 4.7% etc) is found.
    """
    return parse_single_match(words, percentage_re)


def parse_float(words: list) -> float:
    """
    Loop through words and return a float, if a float is found.
    """
    return parse_single_match(words, float_re)


def pick_time(words: list, timezone: str, timestamp: datetime.datetime) -> datetime.datetime:
    if timestamp is None:
        timestamp = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
    for i in range(len(words)):
        w = words[i]
        # Parse HH:MM (-01:45, +01:20, 16:45) format
        match = hhmm_re.findall(w)
        if match:
            match = match[0]
            if match[0] == "-":
                timestamp = timestamp - datetime.timedelta(hours=int(match[1]), minutes=int(match[2]))
            elif match[0] == "+":
                timestamp = timestamp + datetime.timedelta(hours=int(match[1]), minutes=int(match[2]))
            else:
                timestamp = timestamp.replace(hour=int(match[1]), minute=int(match[2]), second=0, microsecond=0)
            timestamp = timestamp.replace(tzinfo=None)
            timestamp = pytz.timezone(timezone).localize(timestamp)
            words.pop(i)
            return timestamp

        # Parse -10m, 10m, +10m minutes format
        match = minute_re.findall(w)
        if match:  # e.g. [('-', '10')]
            match = match[0]
            if match[0] == "-":  # subtract minutes from timestamp
                timestamp = timestamp - datetime.timedelta(minutes=int(match[1]))
            elif match[0] == "+":  # add minutes to timestamp
                timestamp = timestamp + datetime.timedelta(minutes=int(match[1]))
            words.pop(i)
            return timestamp
    return timestamp
