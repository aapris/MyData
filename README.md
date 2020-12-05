# MyData by aapris

The purpose of the project is to be able to gather personal data from various
sources into a single searchable database.

Project contains several Django applications and the database backend is 
PostgreSQL + Postgis, because most of the data is somehow location related.

All data in one database will make much easier to analyze and cross-search 
the data.

Of course most of this data shouldn't be online, but on your personal computer
in encrypted disk and carefully preserved in every way.

## Components

Some day in the future at least these data types will be supported:

* GPS tracks (from GPS loggers, smart watches and mobile apps)
* Media (photos, videos and audio recordings from mobile phones, cameras and camcorders)
* Calendar events

Later it might be interesting to add:

* Emails
* Financial events
* Social media activity
* Health data (from health wearables)
* Sport activities 
* Use of alcohol and drugs
* etc.