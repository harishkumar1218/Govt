#!/bin/bash
set -e

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

if [ $# -eq 0 ]; then
    if [ "$DJANGO_ENV" = "production" ]; then
        echo "Starting Gunicorn..."
        exec gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3
    else
        echo "Starting Django Development Server..."
        exec python manage.py runserver 0.0.0.0:8000
    fi
else
    echo "Executing command: $@"
    exec "$@"
fi
