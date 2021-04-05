import datetime
import json
import logging
import mimetypes
import os
import re
from tempfile import TemporaryFile
from typing import Optional

import pytz
import requests
import telegram
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files import File
from django.core.management.base import BaseCommand
from telegram import ChatAction
from telegram.ext import CallbackContext
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from logbook.models import Alcohol, Keyword, Sensation, Drink, Nutrition, Drug, BaseLogbookModel
from logbook.models import Message, RawFile
from .mytelegrambot import Bot

# TODO: remove debug prints


mimetypes.init()

vol_units = {"l": 1, "dl": 0.1, "cl": 0.01, "ml": 0.001}
weight_units = {"kg": 1, "g": 0.001}

hhmm_re = re.compile(r"([-+])?(\d+):(\d\d)")
minute_re = re.compile(r"([-+])?(\d+)")

float_re = re.compile(r"(\d+\.\d+)")
vol_re = re.compile(r"(\d+\.?\d*)({})".format("|".join(vol_units.keys())))
weight_re = re.compile(r"(\d+\.?\d*)({})".format("|".join(weight_units.keys())))
percentage_re = re.compile(r"(\d+\.?\d*)%")


def download_to_file_field(url: str, filename: str, field: RawFile.file):
    with TemporaryFile() as tf:
        r = requests.get(url, stream=True)
        for chunk in r.iter_content(chunk_size=4096):
            tf.write(chunk)
        tf.seek(0)
        field.save(filename, File(tf), save=True)


def parse_time(timezone: str, time_str: str, timestamp: Optional[datetime.datetime] = None) -> datetime.datetime:
    """
    Parse given string and return timezone aware datetime.
    Time must be in one of following formats:

    now, nyt, 0 or value missing: current time
    -M: M minutes ago, "-10"
    -HH:MM: HH:MM hours and minutes ago, "01:30"
    HH:MM: at HH:MM today, "16:45"
    """
    if timestamp is None:
        timestamp = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)

    # Parse HH:MM (-01:45, +00:20, 16:45) format
    hhmm = hhmm_re.findall(time_str)
    if hhmm:
        hhmm = hhmm[0]
        if hhmm[0] == "-":
            timestamp = timestamp - datetime.timedelta(hours=int(hhmm[1]), minutes=int(hhmm[2]))
        elif hhmm[0] == "+":
            timestamp = timestamp + datetime.timedelta(hours=int(hhmm[1]), minutes=int(hhmm[2]))
        else:
            timestamp = timestamp.replace(hour=int(hhmm[1]), minute=int(hhmm[2]), second=0, microsecond=0)
        timestamp = timestamp.replace(tzinfo=None)
        timestamp = pytz.timezone(timezone).localize(timestamp)
        return timestamp

    # Parse -10, 10, +10 minutes format
    minutes = minute_re.findall(time_str)
    if minutes:
        minutes = minutes[0]
        if minutes[0] == "-":
            return timestamp - datetime.timedelta(minutes=int(minutes[1]))
        elif minutes[0] == "+":
            return timestamp + datetime.timedelta(minutes=int(minutes[1]))
    return timestamp


def parse_message(msg: list):
    print(msg)


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


def save_alcohol(words: list) -> Alcohol:
    """
    Parse details from message text and save an Alcohol instance.
    :param words: original message tokenized
    """
    vol = parse_volume(words)
    percentage = parse_percentage(words)
    return Alcohol(abv=percentage, volume=vol)


def save_sensation(words: list) -> Sensation:
    """
    Parse details from message text and save a Sensation instance.
    :param words: original message tokenized
    :return: created object
    """
    intensity = parse_float(words)
    return Sensation(intensity=intensity)


def save_drink(words: list) -> Drink:
    """
    Parse details from message text and save a Drink instance.
    :param words: original message text tokenized
    :return: created object
    """
    vol = parse_volume(words)
    return Drink(volume=vol)


def save_nutrition(words: list) -> Nutrition:
    """
    Parse details from message text and save a Nutrition instance.
    :param words: original message's text tokenized
    :return: created object
    """
    weight = parse_weight(words)
    return Nutrition(quantity=weight)


def save_drug(words: list) -> Drug:
    """
    Parse details from message text and save a Drug instance.
    :param words: original message's text tokenized
    :return: created object
    """
    weight = parse_weight(words)
    return Drug(quantity=weight)


def save_action(message: Message, words: list, keyword: Keyword, timestamp: datetime.datetime) -> BaseLogbookModel:
    obj = None
    if keyword.model == "Alcohol":
        obj = save_alcohol(words)
    elif keyword.model == "Drug":
        obj = save_drug(words)
    elif keyword.model == "Nutrition":
        obj = save_nutrition(words)
    elif keyword.model == "Drink":
        obj = save_drink(words)
    elif keyword.model == "Sensation":
        obj = save_sensation(words)
    elif keyword.model == "Activity":
        pass
    if obj:
        obj.message = message
        obj.user = message.user
        obj.keyword = keyword.model
        obj.type = words[0].lower()
        obj.name = " ".join(words)
        obj.time = timestamp
        obj.save()
        return obj


def help_cmd(update, context):
    help_msg = "\n".join(
        ["Available commands:", "/help This message", "TODO: implement proper help command instead of this placeholder"]
    )
    context.bot.send_message(chat_id=update.effective_chat.id, text=help_msg)


class MyBot(Bot):
    def __init__(self, token: str, username: str):
        super().__init__(token)
        self.user = User.objects.get(username=username)
        self.timezone = settings.TIME_ZONE

    def set_cmd(self, update: telegram.update.Update, context: CallbackContext):
        print(json.dumps(update.to_dict(), indent=2))
        words = update.message.text.split()
        words.pop(0)  # Remove /set
        if len(words) == 0:
            context.bot.send_message(chat_id=update.effective_chat.id, text="Empty command")
        cmd = words.pop(0)
        if cmd in ["tz", "timezone"]:
            tz = [s for s in pytz.all_timezones if "helsinki".lower() in s.lower()]
            if len(tz) == 1:
                self.timezone = tz[0]
                msg = f"Set timezone to {self.timezone}"
                context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
            else:
                msg = "Found many:\n" + "\n- ".join(tz)
                context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
        else:
            msg = "Unknown setting"
            context.bot.send_message(chat_id=update.effective_chat.id, text=msg)

    def download_files(self, message: Message, update: telegram.update.Update, context: CallbackContext) -> RawFile:
        """
        Download possible file attachment and store it to
        """
        _file = self.get_file_data(update, context)
        if _file:
            url = _file["url"]
            logging.info(f"Downloading file from {url}")
            rf = RawFile(mimetype=_file["mime_type"], message=message)
            download_to_file_field(url, _file["name"], rf.file)
            return rf

    def handle_message(self, update: telegram.update.Update, context: CallbackContext):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
        print(json.dumps(update.to_dict(), indent=2))
        msg_text = self.get_message_text(update)
        # Generate list of strings in message text
        strings = [x for x in msg_text.split(" ") if x]
        # Try to find time shift string
        # TODO: use timeformat with t postfix or something
        if len(strings) > 1:
            timestamp = parse_time(self.timezone, strings[1], update.message.date)
        else:
            timestamp = update.message.date
        print(f"Message time: {timestamp}")
        msg = Message(text=msg_text, user=self.user, time=timestamp, source="telegram", json=update.to_dict())
        msg.save()
        rf = self.download_files(msg, update, context)
        res_msg = []
        if strings:  # E.g. location has empty text
            kw_str = strings[0].lower()
            kws = Keyword.objects.filter(words__contains=[kw_str])
            if kws.count() == 1:
                res_msg.append("Using {}.".format(kws[0].model))
                obj = save_action(msg, strings, kws[0], timestamp)
                print(obj)
            else:
                res_msg.append("Keyword '{}' not found.".format(kw_str))
        else:
            res_msg.append("No message")
        if rf:
            res_msg.append(f"Saved to {rf.file.name}.")
            if rf.mimetype.startswith("image"):
                res_msg.append("Consider sending images as files.")
        context.bot.send_message(chat_id=update.effective_chat.id, text="\n".join(res_msg))

    def handle_edited_message(self, update: telegram.update.Update, context: CallbackContext):
        # TODO: implement editing old Messages using edited_messages
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
        print(json.dumps(update.to_dict(), indent=2))
        res_msg = ["Thank you for editing a message."]
        t = self.get_message_text(update)
        print(f"EDITED {t}")
        context.bot.send_message(chat_id=update.effective_chat.id, text="\n".join(res_msg))

    def poll_forever(self):
        updater = Updater(token=self.token, use_context=True)
        dispatcher = updater.dispatcher
        dispatcher.add_handler(CommandHandler("help", help_cmd))
        dispatcher.add_handler(MessageHandler(Filters.update.message, self.handle_message))
        dispatcher.add_handler(MessageHandler(Filters.update.edited_message, self.handle_edited_message))
        try:
            updater.start_polling()
        except KeyboardInterrupt:
            print("User exit, bye!")


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--log",
            action="store",
            dest="log",
            type=str,
            default="ERROR",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            help="Log level",
        )

        parser.add_argument("--token", action="store", dest="token", required=True, help="Bot token")

        parser.add_argument("--username", action="store", dest="username", required=True, help="username")

    def handle(self, *args, **options):
        logging.basicConfig(format="%(asctime)s %(levelname)-8s %(message)s", level=getattr(logging, options["log"]))
        logging.info("Start bot")
        print(options)
        token = options.get("token")
        if token is None:
            token = os.getenv("LOGBOOKBOT_TOKEN")
            if token is None:
                print("You must give bot token with --token argument or in LOGBOOKBOT_TOKEN environment variable")
                exit(1)
        username = options["username"]
        bot = MyBot(token, username)
        bot.poll_forever()
