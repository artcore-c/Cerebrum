#!/bin/bash
# Stop Cerebrum CM4 Orchestrator

echo "Stopping Cerebrum CM4..."

# Find and kill uvicorn process
pkill -f "uvicorn cerebrum.api.main:app"

if [ $? -eq 0 ]; then
    echo "✓ Cerebrum stopped"
else:
    echo "No running Cerebrum process found"
fi
