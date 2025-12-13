#!/bin/bash
# Sync CM4 code to Raspberry Pi

CM4_USER="${1:-kali}"
CM4_HOST="${2:-100.75.37.26}"
CM4_PATH="/opt/cerebrum"

echo "Syncing to CM4: $CM4_USER@$CM4_HOST:$CM4_PATH"

rsync -avz --progress \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='data/cache' \
    --exclude='logs/*.log' \
    cm4/ "$CM4_USER@$CM4_HOST:$CM4_PATH/"

echo "✓ Sync complete!"
