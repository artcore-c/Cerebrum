#!/bin/bash
# Test Cerebrum CM4 + VPS Connection

source .env

echo "═══════════════════════════════════════"
echo "  Cerebrum System Test"
echo "═══════════════════════════════════════"
echo ""

# Test 1: CM4 Health
echo "1. Testing CM4 Health..."
curl -s http://localhost:${CEREBRUM_PORT}/health | jq '.' || echo "✗ CM4 not responding"
echo ""

# Test 2: VPS Health (via CM4)
echo "2. Testing VPS Connection (via CM4)..."
curl -s http://localhost:${CEREBRUM_PORT}/v1/vps/health | jq '.' || echo "✗ VPS not responding"
echo ""

# Test 3: List Models
echo "3. Listing Available Models..."
curl -s http://localhost:${CEREBRUM_PORT}/v1/models | jq '.' || echo "✗ Failed to list models"
echo ""

# Test 4: Code Completion (simple test)
echo "4. Testing Code Completion..."
curl -s -X POST http://localhost:${CEREBRUM_PORT}/v1/complete \
    -H "Content-Type: application/json" \
    -d '{
        "prompt": "def hello():",
        "language": "python",
        "max_tokens": 50,
        "temperature": 0.2
    }' | jq '.' || echo "✗ Code completion failed"
echo ""

# Test 5: Stats
echo "5. Getting System Stats..."
curl -s http://localhost:${CEREBRUM_PORT}/v1/stats | jq '.cm4' || echo "✗ Failed to get stats"
echo ""

echo "═══════════════════════════════════════"
echo "  Test Complete"
echo "═══════════════════════════════════════"
