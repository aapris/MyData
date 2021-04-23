# Logbook Telegram Bot

`logbookbot.py` is a Django management command, which starts a Telegram bot, 
connects to Telegram API, receives all messages sent to the group 
where bot is invited to and then saves Django data objects 
(logbook.models.Record) based on keywords in messages.

# Installation

## Telegram bot

Read [Telegram's bot documentation](https://core.telegram.org/bots#6-botfather)
how to create a bot (it's very simple) and find its access token.

Create a new Telegram group and invite your bot there 
(search it by name).

Go to group info, click Edit, go to Administrators and make your
bot an admin in Add Admin.

Go back to BotFather, command `/setjoingroups`, choose the new bot
and select **disable**
("block group invitations, the bot can't be added to groups")
so nobody else can find your bot and add it into groups.

## Python3

We assume here there is a working Python >=3.8 environment with all
requirements.txt installed.

## Load initial keywords

Load some sample keywords to the database to get started:

`python manage.py loaddata logbook/fixtures/sample_keywords.json`

Or when using docker-compose:

`docker-compose run django_server python manage.py loaddata logbook/fixtures/sample_keywords.json`

# Usage

## Run command

You can add token as `--token` argument
or in `LOGBOOKBOT_TOKEN` environment variable:

`python manage.py logbootbok --user existing_user --token 123456789:asdfghjjklqwertyuiop123456`

or

`LOGBOOKBOT_TOKEN='123456789:asdfghjjklqwertyuiop123456' python logbookbot.py`

or put it into your .env file, if using docker-compose.

## Send messages

If you loaded sample keywords, you can store logbook records to the database using format
`keyword additional info amount`
e.g.
`alcohol beer 5,0% 33cl Urquell`
or
`drink cola light 0.5l`.
