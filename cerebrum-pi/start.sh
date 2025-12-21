#!/bin/bash
# Start Cerebrum CM4 Orchestrator

set -e

cd /opt/cerebrum-pi

# Activate venv
source venv/bin/activate

# Ensure uvicorn exists
if [ ! -x "venv/bin/uvicorn" ]; then
    echo "ERROR: uvicorn not found in venv"
    exit 1
fi

# Ensure .env exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    exit 1
fi

# Load env
export $(grep -v '^#' .env | xargs)

echo "Starting Cerebrum CM4 Orchestrator..."
echo "Host: ${CEREBRUM_HOST}"
echo "Port: ${CEREBRUM_PORT}"
echo "VPS: ${VPS_ENDPOINT}"
echo ""

# Start server (EXPLICIT PATH)
exec venv/bin/uvicorn cerebrum.api.main:app \
    --host "${CEREBRUM_HOST}" \
    --port "${CEREBRUM_PORT}" \
    --log-level info

