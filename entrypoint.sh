#! /usr/bin/env bash
set -e

DEFAULT_GUNICORN_CONF=/usr/src/crm/gunicorn_conf.py
export GUNICORN_CONF=${GUNICORN_CONF:-$DEFAULT_GUNICORN_CONF}
export WORKER_CLASS=${WORKER_CLASS:-"uvicorn.workers.UvicornWorker"}

# Run database migrations
echo "Running database migrations..."
uv run alembic upgrade head
echo "Migrations completed successfully"

# Initialize admin user if configured
echo "Checking admin initialization..."
uv run crm-admin init
echo "Admin initialization check completed"

# Start Gunicorn
cd src
exec gunicorn -k "$WORKER_CLASS" -c "$GUNICORN_CONF" "main:app"
