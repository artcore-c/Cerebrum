# Cerebrum CM4 Orchestrator

Intelligent code generation system running on Raspberry Pi CM4.

## Architecture

```
CM4 (Orchestrator)     →     VPS (Inference Backend)
Port 7000                     Port 9000
Lightweight API               Heavy model inference
```

## Quick Start

1. **Configure API Key**
   ```bash
   nano .env
   # Add VPS_API_KEY from your VPS
   ```

2. **Start Server**
   ```bash
   ./start.sh
   ```

3. **Test**
   ```bash
   ./test.sh
   ```

## API Endpoints

### Health Check
```bash
curl http://localhost:7000/health
```

### Code Completion
```bash
curl -X POST http://localhost:7000/v1/complete \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "def fibonacci(n):",
    "language": "python",
    "max_tokens": 256
  }'
```

### List Models
```bash
curl http://localhost:7000/v1/models
```

### System Stats
```bash
curl http://localhost:7000/v1/stats
```

## File Structure

```
/opt/cerebrum-pi/
├── cerebrum/
│   ├── core/
│   │   └── vps_client.py       # VPS communication
│   ├── api/
│   │   └── main.py             # Main API server
│   └── ...
├── .env                        # Configuration
├── start.sh                    # Start server
├── stop.sh                     # Stop server
├── test.sh                     # Full system test
└── test_vps.sh                 # Quick VPS test
```

## Troubleshooting

**Can't connect to VPS:**
```bash
# Test VPS directly
./test_vps.sh

# Check Tailscale
sudo tailscale status

# Check VPS is running
ssh unicorn1@173.249.193.188
cd ~/cerebrum-backend
./start.sh
```

**CM4 not starting:**
```bash
# Check logs
./start.sh

# Check if port is in use
sudo lsof -i :7000
```

**API key issues:**
```bash
# Verify .env file
cat .env | grep VPS_API_KEY

# Get key from VPS
ssh unicorn1@173.249.193.188
cat ~/cerebrum-backend/.env | grep CEREBRUM_API_KEY
```

## Development

**Watch logs:**
```bash
./start.sh
# In another terminal:
tail -f logs/cerebrum.log
```

**Manual testing:**
```bash
# Quick health check
curl localhost:7000/health | jq

# Test VPS connection
curl localhost:7000/v1/vps/health | jq
```

## System Requirements

- Raspberry Pi CM4 (4GB+ RAM recommended)
- Debian 12 / Kali Linux
- Python 3.9+
- Network connection to VPS (via Tailscale)

## Performance

- **Local routing:** < 10ms
- **VPS inference:** 1-5 seconds (depending on model size)
- **Memory usage:** ~500MB (CM4)

## Support

Check VPS backend status:
```bash
ssh unicorn1@173.249.193.188
cd ~/cerebrum-backend
./test.sh
```
