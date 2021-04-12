import json
import logging
import mimetypes
import os
from tempfile import TemporaryFile

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
        ["Available commands:", "/help This message", "TODO: implement proper help command instead of this placeholder"]
    )
    context.bot.send_message(chat_id=update.effective_chat.id, text=help_msg)


def create_buttons(update: telegram.update.Update, context: CallbackContext, options: list):
    keyboard = []
    for o in options:
        keyboard.append([InlineKeyboardButton(o[0], callback_data=str(o[1]))])
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


class MyBot(Bot):
    def __init__(self, token: str, username: str):
        super().__init__(token)
        self.user = User.objects.get(username=username)
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
        message_identifier = self.get_message_identifier(update)
        timestamp = update.message.date
        print(f"Message time: {timestamp}")
        msg = Message.objects.create(
            text=msg_text, source="TG", source_id=message_identifier, user=self.user, time=timestamp,
            json=json.dumps(update.to_dict()),
        )
        rec: Record = msg.update_record()
        if rec is None:
            res_msg.append("Record not found")
            kw_str = sanitize_keyword(msg_text.split()[0])
            reply_text = "Keyword '{}' not found. Choose one of these or cancel.".format(kw_str)
            options = [[k.type] for k in Keyword.objects.order_by("type")]
            for o in options:
                o.append(f"newkw:{o[0]}:{kw_str}")
            options.insert(0, ["Cancel", "Cancel query"])
            reply_markup = create_buttons(update, context, options)
            update.message.reply_text(reply_text, reply_markup=reply_markup)
            return
        else:
            res_msg.append(f"Record {rec}")
        rf = self.download_files(msg, update, context)
        if rf:
            res_msg.append(f"Saved to {rf.file.name}.")
            if rf.mimetype.startswith("image"):
                res_msg.append("Consider sending images as files.")
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
