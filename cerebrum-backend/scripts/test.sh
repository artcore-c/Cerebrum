#!/bin/bash
source .env

echo "Testing Cerebrum VPS Backend..."
echo ""

# Health check
echo "Health Check:"
curl -s http://$VPS_BIND_IP:$CEREBRUM_VPS_PORT/health | jq '.'
