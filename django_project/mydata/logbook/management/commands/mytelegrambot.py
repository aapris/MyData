import json
import logging
import mimetypes
import os
import sys
import time
from abc import ABC, abstractmethod

import requests
import telegram
from telegram import ChatAction
from telegram.ext import CallbackContext
from telegram.ext import Updater, MessageHandler, Filters

mimetypes.init()


class Bot(ABC):
    def __init__(self, token: str):
        self.token = token
        self.media_group_ids = {}  # {'12345678906736948': {'text': 'Caption sent with group of documents'}}

    def get_file_data(self, update: telegram.update.Update, context: CallbackContext):
        """
        Get data of certain attachment types from Telegram API.
        "photo" is a special case, because it may contain several instances in a list.

        :param update: Telegram Update object
        :param context:
        :return:

        audio (telegram.Audio, optional)
        document (telegram.Document, optional)
        animation (telegram.Animation, optional)
        game (telegram.Game, optional)
        photo (List[telegram.PhotoSize], optional)
        sticker (telegram.Sticker, optional)
        video (telegram.Video, optional)
        voice (telegram.Voice, optional)
        video_note (telegram.VideoNote, optional)
        """
        _file = {}  # contains all available data of file attachment
        if update.message.photo:  # Loop over photo (List)
            logging.info("photo found")
            max_width = biggest = 0
            for i in range(len(update.message.photo)):  # Pick largest image and store only it
                if max_width < update.message.photo[i]["width"]:
                    max_width = update.message.photo[i]["width"]
                    biggest = i
            _file["type"] = "photo"
            _file["id"] = update.message.photo[biggest]["file_id"]
        for _ttype in ["audio", "document", "video", "voice", "video_note"]:  # Other document types
            if update.message[_ttype]:
                doc = update.to_dict()["message"][_ttype]  # shortcut to message
                logging.info(f"{_ttype} found")
                _file["type"] = _ttype
                _file["mime_type"] = doc["mime_type"]
                _file["id"] = doc["file_id"]
                if doc.get("file_name"):
                    _file["name"] = doc["file_name"]
                break
        if "id" in _file:
            url = f"https://api.telegram.org/bot{self.token}/getFile?file_id={_file['id']}"
            res = requests.get(url)
            filedata = res.json()
            if filedata["ok"]:
                file_path = filedata["result"]["file_path"]
                _file["url"] = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
                if "name" not in _file:
                    _file["name"] = os.path.basename(file_path)
                if "mime_type" not in _file:
                    _file["mime_type"] = mimetypes.types_map.get(os.path.splitext(_file["name"])[1], "")
                return _file
            else:
                logging.warning(filedata)

    def get_message_text(self, update: telegram.update.Update):
        """
        Find out text or caption from message.

        :param update: Telegram Update
        :return: message text
        """
        possible_texts = []
        if update.message:
            possible_texts += [
                update.message.text,
                update.message.caption,
            ]
        if update.edited_message:
            possible_texts += [
                update.edited_message.text,
                update.edited_message.caption,
            ]
        msg_text = next((x for x in possible_texts if x is not None), "")
        msg_text = self.set_media_group_id(update, msg_text)
        return msg_text

    def set_media_group_id(self, update: telegram.update.Update, msg_text: str):
        """
        If media_group_id is present, this Update is part of multi-file post.
        Store msg_text for future use.

        :param update: Telegram Update
        :param msg_text: text or caption from Update
        :return:
        """
        msg = update.to_dict()["message"]
        # First Update has media_group_id and text/caption present
        if "media_group_id" in msg:
            if msg_text != "":
                self.media_group_ids[msg["media_group_id"]] = {
                    "text": msg_text,
                    "time": time.time(),
                }
            elif msg["media_group_id"] in self.media_group_ids:
                msg_text = self.media_group_ids[msg["media_group_id"]]["text"]
                self.media_group_ids[msg["media_group_id"]]["time"] = time.time()
        # Clean up over 60 seconds old media_groups
        for k in list(self.media_group_ids.keys()):
            if self.media_group_ids[k]["time"] + 60 < time.time():
                self.media_group_ids.pop(k)
        return msg_text

    @abstractmethod
    def handle_message(self, update: telegram.update.Update, context: CallbackContext):
        pass

    @abstractmethod
    def handle_edited_message(self, update: telegram.update.Update, context: CallbackContext):
        pass

    @abstractmethod
    def poll_forever(self):
        pass


class DemoBot(Bot):
    def __init__(self, token):
        super().__init__(token)
        self.poll_forever()

    def handle_message(self, update: telegram.update.Update, context: CallbackContext):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
        print(json.dumps(update.to_dict(), indent=2))
        res_msg = ["Thank you for sending a message."]
        filedata = self.get_file_data(update, context)
        print(json.dumps(filedata, indent=2))
        t = self.get_message_text(update)
        print(f"{t}")
        context.bot.send_message(chat_id=update.effective_chat.id, text="\n".join(res_msg))

    def handle_edited_message(self, update: telegram.update.Update, context: CallbackContext):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
        print(json.dumps(update.to_dict(), indent=2))
        res_msg = ["Thank you for editing a message."]
        t = self.get_message_text(update)
        print(f"EDITED {t}")
        context.bot.send_message(chat_id=update.effective_chat.id, text="\n".join(res_msg))

    def poll_forever(self):
        logging.info("Start polling telegram api")
        updater = Updater(token=self.token, use_context=True)
        dispatcher = updater.dispatcher
        dispatcher.add_handler(MessageHandler(Filters.update.message, self.handle_message))
        dispatcher.add_handler(MessageHandler(Filters.update.edited_message, self.handle_edited_message))
        try:
            updater.start_polling()
        except KeyboardInterrupt:
            print("User exit, bye!")


def usage():
    t = "Usage: python3 {} <your telegram bot token>".format(sys.argv[0])
    print(t)
    exit()


def main(token):
    DemoBot(token)


if __name__ == "__main__":

    if len(sys.argv) == 1:
        usage()

    main(sys.argv[1])
