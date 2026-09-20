#!/bin/bash
# IDX Stock Analyzer - Startup Script

set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$APP_DIR/venv"
LOG_DIR="$APP_DIR/logs"

# Create logs directory
mkdir -p "$LOG_DIR"

# Activate virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install -r "$APP_DIR/requirements.txt" --upgrade --quiet

# Initialize database
cd "$APP_DIR"
python3 -c "
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname('.'), 'backend'))
from database import init_db
init_db()
print('Database initialized.')
"

# Start the application
echo "Starting IDX Stock Analyzer on port 8000..."
exec uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 2 \
    --access-log \
    --log-level info
