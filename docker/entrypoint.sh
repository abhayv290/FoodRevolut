#!/bin/sh
set -e

echo "⏳ Waiting for database..."

MAX_RETRIES=20
COUNT=0

until python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')
django.setup()
from django.db import connection
connection.ensure_connection()
" > /dev/null 2>&1; do
    COUNT=$((COUNT+1))
    if [ $COUNT -ge $MAX_RETRIES ]; then
        echo "❌ Database not reachable after $MAX_RETRIES attempts. Exiting..."
        exit 1
    fi
    echo "  Database not ready — retrying in 2 seconds... ($COUNT/$MAX_RETRIES)"
    sleep 2
done

echo "✅ Database ready"

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "🔄 Running migrations..."
    python manage.py migrate --noinput
fi

# ── collectstatic disabled by default ────────────────────────────────────────
# S3 static files are uploaded separately in CI/CD pipeline
# Only enable manually when static files change
if [ "${RUN_COLLECTSTATIC:-false}" = "true" ]; then
    echo "📁 Collecting static files..."
    python manage.py collectstatic --noinput --clear
fi

echo "🚀 Starting: $@"
exec "$@"