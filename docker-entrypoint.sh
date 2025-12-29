#!/bin/bash
set -e

# Function to check database connection
check_db() {
  python << END
import sys
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    sys.exit(0)
except Exception:
    sys.exit(1)
END
}

# Wait for database to be ready
echo "Waiting for database..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
  if check_db; then
    echo "Database is up - continuing..."
    break
  fi
  attempt=$((attempt + 1))
  echo "Database is unavailable - sleeping (attempt $attempt/$max_attempts)"
  sleep 2
done

if [ $attempt -eq $max_attempts ]; then
  echo "Database connection failed after $max_attempts attempts"
  exit 1
fi

# Apply migrations (will only apply if there are pending migrations)
echo "Applying migrations..."
python manage.py migrate --noinput

# Collect static files (in case they weren't collected at build time)
echo "Collecting static files..."
python manage.py collectstatic --noinput || true

# Execute the main command
exec "$@"
