#!/bin/bash
# Start Cerebrum CM4 Orchestrator

cd /opt/cerebrum-pi

# Activate venv
source venv/bin/activate

# Sanity check
if [ ! -x "venv/bin/uvicorn" ]; then
    echo "ERROR: uvicorn not found in venv"
    exit 1
fi

# Load environment
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    exit 1
fi

export $(grep -v '^#' .env | xargs)

# Check API key
if [ -z "$VPS_API_KEY" ] || [ "$VPS_API_KEY" == "RzNR7FfyEsrsyG8UPflpjTMMshyz4sp4" ]; then
    echo "WARNING: VPS_API_KEY not configured!"
    echo "Edit .env and add the API key from your VPS"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "Starting Cerebrum CM4 Orchestrator..."
echo "Host: $CEREBRUM_HOST"
echo "Port: $CEREBRUM_PORT"
echo "VPS: $VPS_ENDPOINT"
echo ""

# Start server (EXPLICIT PATH)
exec venv/bin/uvicorn cerebrum.api.main:app \
    --host $CEREBRUM_HOST \
    --port $CEREBRUM_PORT \
    --log-level info

