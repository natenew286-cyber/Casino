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

# Final validation with Django before proceeding
echo "Performing final Django connection validation..."
if ! check_db_django; then
  echo "✗ Django database connection validation failed"
  echo "The database is reachable but Django cannot connect properly."
  echo "Check your DATABASES configuration in settings."
  exit 1
fi

# Apply migrations (will only apply if there are pending migrations)
echo "Applying database migrations..."
python manage.py migrate --noinput

# Collect static files (in case they weren't collected at build time)
echo "Collecting static files..."
python manage.py collectstatic --noinput || true

echo "✓ Initialization complete!"
echo "Starting application..."

# Execute the main command
exec "$@"