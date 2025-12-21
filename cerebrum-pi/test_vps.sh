#!/bin/bash
set -euo pipefail

# Quick test VPS connection

if [ ! -f .env ]; then
    echo "✗ .env file not found"
    exit 1
fi

source .env

command -v curl >/dev/null || { echo "✗ curl not installed"; exit 1; }
command -v jq   >/dev/null || { echo "✗ jq not installed"; exit 1; }

echo "Testing VPS Backend..."
echo "Endpoint: $VPS_ENDPOINT"
echo ""

HTTP_CODE=$(curl -s -o /tmp/vps_health.json -w "%{http_code}" \
    "$VPS_ENDPOINT/health")

if [ "$HTTP_CODE" != "200" ]; then
    echo "✗ VPS health check failed (HTTP $HTTP_CODE)"
    cat /tmp/vps_health.json || true
    exit 1
fi

jq '.' /tmp/vps_health.json
echo ""
echo "✓ VPS is reachable and healthy"
