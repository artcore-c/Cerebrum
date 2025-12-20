#!/bin/bash
cd ~/cerebrum-backend
source venv/bin/activate
export $(cat .env | grep -v '^#' | xargs)

echo "Starting Cerebrum VPS Backend..."
echo "Bind IP: $VPS_BIND_IP"
echo "Port: $CEREBRUM_VPS_PORT"

uvicorn vps_server.main:app \
    --host $VPS_BIND_IP \
    --port $CEREBRUM_VPS_PORT \
    --workers 1 \
    --log-level info
