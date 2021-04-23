import json
import logging
import mimetypes
import os
from collections import Counter
from tempfile import TemporaryFile
from typing import List

import pytz
import requests
import telegram
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files import File
from django.core.management.base import BaseCommand
from telegram import ChatAction
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.callbackquery import CallbackQuery
from telegram.ext import CallbackContext
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.ext.callbackqueryhandler import CallbackQueryHandler

from logbook.models import Keyword, Record, Profile
from logbook.models import Message, Attachment
from logbook.utils import sanitize_keyword
from .mytelegrambot import Bot

mimetypes.init()


def download_to_file_field(url: str, filename: str, field: Attachment.file):
    with TemporaryFile() as tf:
        r = requests.get(url, stream=True)
        for chunk in r.iter_content(chunk_size=4096):
            tf.write(chunk)
        tf.seek(0)
        field.save(filename, File(tf), save=True)


def parse_message(msg: list):
    print(msg)


def help_cmd(update, context):
    help_msg = "\n".join(
        [
            "Available commands:",
            "/help This message",
            "/show keyword: show latest records of keyword",
        ]
    )
    context.bot.send_message(chat_id=update.effective_chat.id, text=help_msg)


def create_buttons(update: telegram.update.Update, context: CallbackContext, options: list):
    keyboard = []
    for o in options:
        keyboard.append([InlineKeyboardButton(o[0], callback_data=str(o[1]))])
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


def create_buttons_edit(update: telegram.update.Update, context: CallbackContext, options: list):
    keyboard = []
    for o in options:
        keyboard.append([InlineKeyboardButton(o[0], switch_inline_query_current_chat=str(o[1]))])
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


def strip_trailing_zeroes(num) -> str:
    """Remove trailing zeroes, e.g. 0.500 --> 0.5 and 1.000 -> 1"""
    s = "{:.3f}".format(num)
    return s.rstrip("0").rstrip(".") if "." in s else s


def create_message(kw_str, r) -> List[str]:
    words = [kw_str, r.description]
    if r.quantity is not None:
        words.append("{}g".format(strip_trailing_zeroes(r.quantity * 1000)))
    if r.abv is not None:
        words.append("{}%".format(strip_trailing_zeroes(r.abv)))
    if r.volume is not None:
        words.append("{}l".format(strip_trailing_zeroes(r.volume)))
    return words


def options_for_keyword(kw_str, count=3) -> list:
    records = Record.objects.filter(name=kw_str).order_by("-time")
    # Grab latest unique messages for this keyword
    latest_descriptions = []
    latest_messages = []
    for r in records:
        if r.description not in latest_descriptions:
            latest_descriptions.append(r.description)
            latest_messages.append(create_message(kw_str, r))
        if len(latest_descriptions) == count:
            break
    # Grab most common messages for this keyword
    common_messages = []
    descriptions = [r.description for r in records[:100]]
    occurrences = Counter(descriptions)
    most_common = [o[0] for o in occurrences.most_common()]
    for r in most_common:
        r = records.filter(description=r)[0]
        message = create_message(kw_str, r)
        if message not in latest_messages:
            common_messages.append(message)
        if len(common_messages) == count:
            break
    all_messages = latest_messages + common_messages
    # Create list of latest and most common messages
    options = [[" ".join(m)] for m in all_messages]
    for o in options:  # options is a list of 2-item lists (button_text, button_value)
        o.append(o[0])
    return options


class MyBot(Bot):
    def __init__(self, token: str, username: str):
        super().__init__(token)
        self.user, created = User.objects.get_or_create(username=username)
        if created:
            logging.warning(f"Created a new user {username}")
        self.timezone = settings.TIME_ZONE
        if hasattr(self.user, "profile") is False:  # Create a Profile for User, if it doesn't exist
            Profile.objects.create(user=self.user, timezone=self.timezone)

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

    def show_cmd(self, update: telegram.update.Update, context: CallbackContext):
        print(json.dumps(update.to_dict(), indent=2))
        msg = []
        words = update.message.text.split()
        words.pop(0)  # Remove /show
        if len(words) == 0:
            keywords = ", ".join([k[0] for k in Keyword.objects.values_list("type").order_by("type")])
            msg.append(f"Add keyword after show command, e.g. one of {keywords}")
            context.bot.send_message(chat_id=update.effective_chat.id, text="\n".join(msg))
            return
        kw_str = words[0]
        keywords = Keyword.objects.filter(type__iexact=kw_str)
        if len(keywords) == 1:
            records = Record.objects.filter(keyword=keywords[0]).order_by("-time")
        else:
            records = Record.objects.filter(name=kw_str).order_by("-time")
        for r in records[:10]:
            tstr = r.time.astimezone(pytz.timezone(self.timezone)).strftime("%d.%m %H:%M")
            msg.append("{} {}".format(tstr, " ".join(create_message(r.name, r))))
        context.bot.send_message(chat_id=update.effective_chat.id, text="\n".join(msg))

    def reply_query(self, update: telegram.update.Update, context: CallbackContext):
        """
        Callback method handling button press.
        """
        # getting the callback query
        # documentation: https://python-telegram-bot.readthedocs.io/en/stable/telegram.callbackquery.html
        query: CallbackQuery = update.callback_query

        # CallbackQueries need to be answered, even if no notification to the user is needed
        # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
        # documentation: https://python-telegram-bot.readthedocs.io/en/stable/telegram.callbackquery.html#telegram.CallbackQuery.answer
        query.answer()

        # editing message sent by the bot
        # documentation: https://python-telegram-bot.readthedocs.io/en/stable/telegram.callbackquery.html#telegram.CallbackQuery.edit_message_text
        cmd = query.data.split(":")
        res_text = []
        if len(cmd) == 3:
            if cmd[0] == "newkw":
                kw = Keyword.objects.get(type=cmd[1])
                kw.words.append(cmd[2].lower())
                kw.save()
                res_text.append(f"New keyword created for {cmd[1]}. Current keywords are:")
                res_text.append(", ".join(kw.words))
                res_text.append("You must now edit original message to make it processed properly.")
                res_text.append("Add a new space character between some words.")
        else:
            res_text.append(f"Unknown reply: '{query.data}'.")
        query.edit_message_text(text="\n".join(res_text))

    def download_files(self, message: Message, update: telegram.update.Update, context: CallbackContext) -> Attachment:
        """
        Download possible file attachment and store it to
        """
        _file = self.get_file_data(update, context)
        if _file:
            url = _file["url"]
            logging.info(f"Downloading file from {url}")
            rf = Attachment(mimetype=_file["mime_type"], message=message)
            download_to_file_field(url, _file["name"], rf.file)
            return rf

    def handle_message(self, update: telegram.update.Update, context: CallbackContext):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
        res_msg = []
        print(json.dumps(update.to_dict(), indent=2))
        msg_text = self.get_message_text(update)
        if msg_text.startswith("@"):
            words = msg_text.split()
            words.pop(0)
            msg_text = " ".join(words)
        if msg_text == "":  # Do nothing if message was empty
            return
        kw_str = sanitize_keyword(msg_text.split()[0])
        message_identifier = self.get_message_identifier(update)
        timestamp = update.message.date
        logging.info(f"Message time: {timestamp}, text: {msg_text}")
        msg = Message.objects.create(
            text=msg_text, source="TG", source_id=message_identifier, user=self.user, time=timestamp,
            json=json.dumps(update.to_dict()),
        )
        rec: Record = msg.update_record()
        if rec is None and msg_text != "":
            # res_msg.append("Record not found")
            kws = Keyword.objects.filter(words__contains=[kw_str])
            if kws.count() == 1:  # keyword found, requested latest records?
                reply_text = "Keyword '{}' found. Choose one of these or cancel.".format(kw_str)
                options = options_for_keyword(kw_str, 3)
                options.insert(0, ["Cancel", ""])
                reply_markup = create_buttons_edit(update, context, options)
            else:
                reply_text = "Keyword '{}' not found. Choose one of these or cancel.".format(kw_str)
                options = [[k.type] for k in Keyword.objects.order_by("type")]
                for o in options:
                    o.append(f"newkw:{o[0]}:{kw_str}")
                options.insert(0, ["Cancel", "Cancel query"])
                reply_markup = create_buttons(update, context, options)
            update.message.reply_text(reply_text, reply_markup=reply_markup)
            return
        else:
            res_msg.append(" ".join(create_message(kw_str, rec)))
        rf = self.download_files(msg, update, context)
        if rf:
            res_msg.append(f"Saved to {rf.file.name}.")
            # if rf.mimetype.startswith("image"):
            #     res_msg.append("Consider sending images as files.")
        context.bot.send_message(chat_id=update.effective_chat.id, text="\n".join(res_msg))

    def handle_edited_message(self, update: telegram.update.Update, context: CallbackContext):
        # NOTE: work in progress
        # TODO: finish implement editing old Messages using edited_messages
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
        print(json.dumps(update.to_dict(), indent=2))
        message_identifier = self.get_message_identifier(update)
        msg = Message.objects.get(source_id=message_identifier)
        res_msg = ["Thank you for editing a message."]
        t = self.get_message_text(update)
        msg.text = t
        msg.json = json.dumps(update.to_dict())
        msg.update_record()
        print(f"EDITED {t}")
        msg.save()
        if hasattr(msg, "record"):
            res_msg.append(f"Record {msg.record}")
        context.bot.send_message(chat_id=update.effective_chat.id, text="\n".join(res_msg))

    def poll_forever(self):
        updater = Updater(token=self.token, use_context=True)
        dispatcher = updater.dispatcher
        dispatcher.add_handler(CommandHandler("help", help_cmd))
        dispatcher.add_handler(CommandHandler("set", self.set_cmd))
        dispatcher.add_handler(CommandHandler("show", self.show_cmd))
        dispatcher.add_handler(CallbackQueryHandler(self.reply_query))  # handling inline buttons pressing
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
            default="INFO",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            help="Log level",
        )
        parser.add_argument("--token", help="Bot token", default=os.getenv("LOGBOOKBOT_TOKEN"))
        parser.add_argument("--username", help="Django username", default=os.getenv("DJANGO_USERNAME"))

    def handle(self, *args, **options):
        logging.basicConfig(format="%(asctime)s %(levelname)-8s %(message)s", level=getattr(logging, options["log"]))
        logging.info("Start bot")
        token = options.get("token")
        username = options.get("username")
        if token is None:
            print("You must give bot token with --token argument or in LOGBOOKBOT_TOKEN environment variable")
            exit(1)
        if username is None:
            print("You must give username with --username argument or in DJANGO_USERNAME environment variable")
            exit(1)
        bot = MyBot(token, username)
        bot.poll_forever()
