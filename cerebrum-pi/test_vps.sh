#!/bin/bash
# Quick test VPS connection

source .env

echo "Testing VPS Backend..."
echo "Endpoint: $VPS_ENDPOINT"
echo ""

# Test health endpoint
curl -s $VPS_ENDPOINT/health | jq '.'

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ VPS is reachable!"
else
    echo ""
    echo "✗ Cannot reach VPS"
    echo "Check:"
    echo "  1. Is VPS running? (ssh to VPS: ~/cerebrum-backend/start.sh)"
    echo "  2. Can you reach VPS? (ping 127.0.0.1:9000)"
    echo "  3. Is Tailscale running?"
fi
