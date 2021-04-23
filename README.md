# MyData by aapris

The purpose of the project is to be able to gather personal data from various
sources into a single searchable database.

Project contains several Django applications and the database backend is 
PostgreSQL + PostGIS, because most of the data is somehow location related.

All data in one database will make much easier to analyze and cross-search 
the data.

Of course most of this data shouldn't be online, but on your personal computer
in encrypted disk and carefully preserved in every way.

## Components

Currently supported data types are:

* GPS tracks (from GPS loggers, smart watches and mobile apps)
* Calendar events (timeline)
* Daily events (logbook, e.g. eaten food, drinks, felt pain and sensations, use of alcohol and drugs)

Some day in the future at least these data types will be supported:

* Media (photos, videos and audio recordings from mobile phones, cameras and camcorders)

Later it might be interesting to add:

* Emails
* Financial events
* Social media activity
* Health data (from health wearables)
* Sport activities 
* etc.

# Running project

Clone this project first to a local directory, create

```
git clone https://github.com/aapris/MyData.git
cd MyData
```


## Create .env.dev

Copy `.env.dev-sample` to `.env.dev`.

If you want to run python app locally (not in Docker container),
you can activate environment variables running this command
(change env file name if needed):

`export $(grep '^\w' env.local | xargs)`

## Docker

Run first  

`docker-compose up -d --build`  
and then  
`docker-compose up`

Building project takes currently a few minutes.

## Virtuanenv

In MyData directory:

```
python3 -m venv venv
source venv/bin/activate
```

## Django server

`cd services/django_server/mydata/ && python manage.py runserver`

## Logbook telegram bot

`cd services/django_server/mydata/ && python manage.py logbookbot`
