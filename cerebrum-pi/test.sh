#!/bin/bash
set -euo pipefail

if [ ! -f .env ]; then
    echo "✗ .env file not found"
    exit 1
fi

source .env

command -v curl >/dev/null || { echo "✗ curl not installed"; exit 1; }
command -v jq   >/dev/null || { echo "✗ jq not installed"; exit 1; }

RUN_INFERENCE_TEST=${RUN_INFERENCE_TEST:-0}

echo "═══════════════════════════════════════"
echo "  Cerebrum System Test"
echo "═══════════════════════════════════════"
echo ""

# Test 1: CM4 Health
echo "1. Testing CM4 Health..."
HTTP_CODE=$(curl -s -o /tmp/cm4_health.json -w "%{http_code}" \
    "http://localhost:${CEREBRUM_PORT}/health")

if [ "$HTTP_CODE" != "200" ]; then
    echo "✗ CM4 health check failed (HTTP $HTTP_CODE)"
    exit 1
fi

jq '.' /tmp/cm4_health.json
echo "✓ CM4 is healthy"
echo ""

# Test 2: VPS Health (via CM4)
echo "2. Testing VPS Connection (via CM4)..."
HTTP_CODE=$(curl -s -o /tmp/vps_via_cm4.json -w "%{http_code}" \
    "http://localhost:${CEREBRUM_PORT}/v1/vps/health")

if [ "$HTTP_CODE" != "200" ]; then
    echo "✗ VPS health via CM4 failed (HTTP $HTTP_CODE)"
    exit 1
fi

jq '.' /tmp/vps_via_cm4.json
echo "✓ VPS reachable via CM4"
echo ""

# Test 3: List Models
echo "3. Listing Available Models..."
curl -s "http://localhost:${CEREBRUM_PORT}/v1/models" | jq '.'
echo ""

# Test 4: Code Completion (optional)
if [ "$RUN_INFERENCE_TEST" -eq 1 ]; then
    echo "4. Testing Code Completion..."
    curl -s -X POST "http://localhost:${CEREBRUM_PORT}/v1/complete" \
        -H "Content-Type: application/json" \
        -d '{
            "prompt": "def hello():",
            "language": "python",
            "max_tokens": 32,
            "temperature": 0.2
        }' | jq '.'
    echo ""
else
    echo "4. Skipping inference test (RUN_INFERENCE_TEST=0)"
    echo ""
fi

# Test 5: Stats
echo "5. Getting System Stats..."
curl -s "http://localhost:${CEREBRUM_PORT}/v1/stats" | jq '.cm4'
echo ""

echo "═══════════════════════════════════════"
echo "  Test Complete"
echo "═══════════════════════════════════════"

