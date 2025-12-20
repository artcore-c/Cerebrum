#!/bin/bash
# Start Cerebrum CM4 Orchestrator

cd /opt/cerebrum-pi
source venv/bin/activate

# Check if .env exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Run: cp .env.example .env"
    echo "Then edit .env with your VPS_API_KEY"
    exit 1
fi

# Load environment
export $(cat .env | grep -v '^#' | xargs)

# Check API key
if [ -z "$VPS_API_KEY" ] || [ "$VPS_API_KEY" == "your-api-key-from-vps-here" ]; then
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

# Start server
uvicorn cerebrum.api.main:app \
    --host $CEREBRUM_HOST \
    --port $CEREBRUM_PORT \
    --log-level info
