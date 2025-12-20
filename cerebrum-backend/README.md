# Cerebrum VPS Backend

Lightweight inference backend for heavy model computation.

## Quick Start

1. **Generate API Key**
   ```bash
   ./generate_api_key.sh
   ```

2. **Configure .env**
   ```bash
   nano .env
   # Add the generated API key
   ```

3. **Start Server**
   ```bash
   ./start.sh
   ```

4. **Test**
   ```bash
   ./test.sh
   ```

## Manual Commands

```bash
# Start
./start.sh

# Stop
./stop.sh

# Test
./test.sh

# Check logs
tail -f logs/backend.log
```

## Systemd Service

For auto-start on boot:

```bash
sudo cp cerebrum-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable cerebrum-backend
sudo systemctl start cerebrum-backend

# Check status
sudo systemctl status cerebrum-backend

# View logs
sudo journalctl -u cerebrum-backend -f
```

## API Endpoints

- `GET /health` - Health check (no auth)
- `POST /v1/inference` - Run inference (requires API key)
- `GET /v1/models` - List models (requires API key)
- `GET /v1/stats` - System statistics (requires API key)
- `POST /v1/unload/{model}` - Unload model (requires API key)

## Configuration

Edit `.env`:
- `CEREBRUM_API_KEY` - API authentication key
- `VPS_BIND_IP` - Local Host (127.0.0.1)
- `CEREBRUM_VPS_PORT` - Port (9000)
- `MAX_CPU_PERCENT` - Max CPU before rejecting requests (70)
- `IOS_BACKEND_PORT` - iOS backend port to monitor (8000)

## Model Management

Models are cached in RAM after first use. They auto-unload after 60 minutes of inactivity.

**Manual cleanup:**
```bash
curl -X POST -H "X-API-Key: YOUR_KEY" http://127.0.0.1:9000/v1/cleanup
```

## Monitoring

```bash
# Watch system resources
watch 'curl -s http://127.0.0.1:9000/health | jq'

# Check stats
curl -H "X-API-Key: YOUR_KEY" http://127.0.0.1:9000/v1/stats | jq
```

## Security

- API key authentication required for all inference endpoints
- Health endpoint is public (for monitoring)
- Binds to Tailscale IP only (not public)
- Respects iOS backend priority (reduces load when active)

## Resource Protection

- Automatically rejects requests when CPU > 70%
- Automatically rejects when RAM < 1GB available
- Prioritizes iOS backend (reduces threshold to 50% when active)
- Models auto-unload after inactivity

## Troubleshooting

**Can't connect:**
```bash
# Check if running
ps aux | grep uvicorn

# Check port
sudo lsof -i :9000

# Test locally
curl http://127.0.0.1:9000/health
```

**High CPU:**
```bash
# Check what's using CPU
top

# Unload unused models
curl -X POST -H "X-API-Key: KEY" http://127.0.0.1:9000/v1/cleanup
```

**Out of RAM:**
```bash
# Check memory
free -h

# Unload models manually
curl -X POST -H "X-API-Key: KEY" http://127.0.0.1:9000/v1/unload/model_name
```
