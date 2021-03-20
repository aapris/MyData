# Logbook Telegram Bot

`logbookbot.py` is a Django management command, which starts a Telegram bot, connects to Telgram API, receives all
messages sent to the group where bot is invited and then saves Django data objects based on commands in messages.

Data objects are logbook entries

# Installation

## Telegram bot

Read [Telegram's bot documentation](https://core.telegram.org/bots#6-botfather)
how to create a bot and find its access token.

## Python3

Create a Python3 virtuanenv, activate it and install required modules:

`pip install -r requirements.txt -U`

# Usage

## Load intial keywords

Load some sample keywords to the database to get started:

`python manage.py loaddata logbook/fixtures/sample_keywords.json`

## Run command

You can add token as `--token` argument
~~or in `LOGBOOKBOT_TOKEN` environment variable~~:

`python manage.py logbootbok --user existing_user --token 123456789:asdfghjjklqwertyuiop123456`

~~or~~

~~LOGBOOKBOT_TOKEN='123456789:asdfghjjklqwertyuiop123456' python justnow_telegrambot.py~~

## Send messages

If you loaded sample keywords, you can store logbook entries to the database using format
`keyword additional info amount`
e.g.
`alcohol beer 5,0% 33cl Urquell`
or
`drink cola light 0.5l `.
