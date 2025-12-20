#!/bin/bash
API_KEY=$(openssl rand -base64 32 | tr -d /=+ | cut -c1-32)
echo ""
echo "Generated secure API key:"
echo "════════════════════════════════════════"
echo "$API_KEY"
echo "════════════════════════════════════════"
echo ""
echo "Add this to your .env file:"
echo "CEREBRUM_API_KEY=$API_KEY"
