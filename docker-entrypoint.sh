#!/bin/bash
set -e

# Extract database connection info from environment variables
DB_HOST="${DATABASE_HOST:-${DB_HOST:-localhost}}"
DB_PORT="${DATABASE_PORT:-${DB_PORT:-5432}}"
DB_NAME="${DATABASE_NAME:-${DB_NAME:-postgres}}"
DB_USER="${DATABASE_USER:-${DB_USER:-postgres}}"
DB_PASSWORD="${DATABASE_PASSWORD:-${DB_PASSWORD:-}}"

echo "Database connection target: ${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

# Method 1: Check using pg_isready (fastest, least dependencies)
check_db_pg_isready() {
  if command -v pg_isready > /dev/null 2>&1; then
    if [ -n "$DB_PASSWORD" ]; then
      PGPASSWORD="$DB_PASSWORD" pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1
    else
      pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1
    fi
    return $?
  fi
  return 1
}

# Method 2: Check using raw TCP connection (works even if PostgreSQL tools aren't available)
check_db_tcp() {
  if command -v nc > /dev/null 2>&1; then
    nc -z -w2 "$DB_HOST" "$DB_PORT" > /dev/null 2>&1
    return $?
  elif command -v timeout > /dev/null 2>&1; then
    timeout 2 bash -c "cat < /dev/null > /dev/tcp/${DB_HOST}/${DB_PORT}" > /dev/null 2>&1
    return $?
  fi
  return 1
}

# Method 3: Check using psycopg2 directly (bypasses Django setup issues)
check_db_psycopg2() {
  python << END
import sys
try:
    import psycopg2
    conn = psycopg2.connect(
        host='${DB_HOST}',
        port='${DB_PORT}',
        dbname='${DB_NAME}',
        user='${DB_USER}',
        password='${DB_PASSWORD}',
        connect_timeout=5
    )
    conn.close()
    sys.exit(0)
except Exception as e:
    sys.exit(1)
END
}

# Method 4: Check using Django ORM (most thorough, but requires Django setup)
check_db_django() {
  python << END
import sys
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.base')
try:
    django.setup()
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    sys.exit(0)
except Exception:
    sys.exit(1)
END
}

# Check Valkey (Redis-compatible) connection
check_redis() {
  python << END
import sys
import os
import valkey
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
try:
    # simple parsing
    r = valkey.from_url(redis_url, socket_timeout=2)
    r.ping()
    sys.exit(0)
except Exception as e:
    sys.exit(1)
END
}

# Comprehensive check function that tries all methods
check_db() {
  local method_name=$1
  
  case $method_name in
    "pg_isready")
      check_db_pg_isready
      return $?
      ;;
    "tcp")
      check_db_tcp
      return $?
      ;;
    "psycopg2")
      check_db_psycopg2
      return $?
      ;;
    "django")
      check_db_django
      return $?
      ;;
    *)
      # Try all methods in order until one succeeds
      if check_db_pg_isready; then
        echo "  ✓ pg_isready check passed"
        return 0
      fi
      
      if check_db_tcp; then
        echo "  ✓ TCP connection check passed"
        return 0
      fi
      
      if check_db_psycopg2; then
        echo "  ✓ psycopg2 connection check passed"
        return 0
      fi
      
      if check_db_django; then
        echo "  ✓ Django ORM check passed"
        return 0
      fi
      
      return 1
      ;;
  esac
}

# Wait for database to be ready
echo "Waiting for database to be ready..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
  if check_db "all"; then
    echo "✓ Database is ready!"
    break
  fi
  
  attempt=$((attempt + 1))
  echo "  Database unavailable (attempt $attempt/$max_attempts) - retrying in 2s..."
  sleep 2
done

if [ $attempt -eq $max_attempts ]; then
  echo "✗ Database connection failed after $max_attempts attempts"
  echo "Connection details: ${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
  echo "Please check:"
  echo "  - Database container is running"
  echo "  - Database credentials are correct"
  echo "  - Network connectivity between containers"
  exit 1
fi

# Wait for Valkey (Redis-compatible) to be ready
echo "Waiting for Valkey to be ready..."
redis_attempts=30
r_attempt=0

while [ $r_attempt -lt $redis_attempts ]; do
  if check_redis; then
    echo "✓ Valkey is ready!"
    break
  fi
  
  r_attempt=$((r_attempt + 1))
  echo "  Valkey unavailable (attempt $r_attempt/$redis_attempts) - retrying in 2s..."
  sleep 2
done

if [ $r_attempt -eq $redis_attempts ]; then
  echo "✗ Valkey connection failed after $redis_attempts attempts"
  echo "Please check REDIS_URL environment variable."
  # We don't exit here because sometimes Valkey is optional or used only for caching/celery
  # but strictly speaking if Celery is required, this is fatal.
  # Given the user's request, we will warn loudly but maybe let it proceed 
  # OR exit 1 if they want strict checking. 
  # For safety in this specific context (Celery worker crash loop), failure is better.
  echo "CRITICAL: Valkey is not reachable. Celery worker will likely fail."
  exit 1
fi

# Final validation with Django before proceeding
echo "Performing final Django connection validation..."
if ! check_db_django; then
  echo "✗ Django database connection validation failed"
  echo "The database is reachable but Django cannot connect properly."
  echo "Check your DATABASES configuration in settings."
  exit 1
fi

# Create migrations if they don't exist
echo "Creating migrations if needed..."
python manage.py makemigrations --noinput || true

# Apply migrations (will only apply if there are pending migrations)
# Django will automatically handle dependencies and migrate accounts first
echo "Applying database migrations..."
python manage.py migrate --noinput

# Collect static files (in case they weren't collected at build time)
echo "Collecting static files..."
python manage.py collectstatic --noinput || true

echo "✓ Initialization complete!"
echo "Starting application..."

# Execute the main command
exec "$@"