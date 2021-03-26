# Timeline

Timeline app stores currently Event objects, 
which are virtually calendar events.

## Usage

Load events from .ics file (e.g. exported from Google calendar):  
`python manage.py process_ics --uri path/to/user_gmail.com.ics --source user@gmail.com --username user`

# TODO

* add REST API
* implement more importers:
  * Swarm/Foursquare
  * Google maps
* consider having Checkin model