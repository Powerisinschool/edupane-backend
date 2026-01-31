#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Run database migrations
echo "Running Migrations..."
python manage.py migrate

echo "Checking/Creating Admin User..."
python create_admin.py

# Start Celery Worker in the background (&)
echo "Starting Celery Worker..."
celery -A edupane_backend worker --loglevel=info --concurrency=1 &

# Start Celery Beat in the background (&)
echo "Starting Celery Beat..."
celery -A edupane_backend beat -l info &

# Start Daphne (The Main Process)
# We do NOT use '&' here because Render listens to this process to know the app is alive
echo "Starting Daphne..."
daphne -b 0.0.0.0 -p 10000 edupane_backend.asgi:application
