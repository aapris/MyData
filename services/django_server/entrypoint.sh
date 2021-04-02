#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $POSTGRESQL_HOST $POSTGRESQL_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

pip install -r requirements.txt
python manage.py migrate

exec "$@"
