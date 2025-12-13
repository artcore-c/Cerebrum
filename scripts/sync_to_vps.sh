#!/bin/bash
# Sync VPS code to server

VPS_USER="${1:-unicorn1}"
VPS_HOST="${2:-100.78.22.113}"
VPS_PATH="~/cerebrum-backend"

echo "Syncing to VPS: $VPS_USER@$VPS_HOST:$VPS_PATH"

rsync -avz --progress \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='logs/*.log' \
    vps/ "$VPS_USER@$VPS_HOST:$VPS_PATH/"

echo "✓ Sync complete!"
