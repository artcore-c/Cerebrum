#!/bin/bash
# Sync Cerebrum VPS backend code to server

VPS_USER="${1:-unicorn1}"
VPS_HOST="${2:-100.78.22.113}"
VPS_PATH="/home/unicorn1/cerebrum-backend"

echo "Syncing cerebrum-backend to VPS: $VPS_USER@$VPS_HOST:$VPS_PATH"

rsync -avz --progress \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='logs/*.log' \
    cerebrum-backend/ \
    "$VPS_USER@$VPS_HOST:$VPS_PATH/"

echo "✓ Sync complete!"

