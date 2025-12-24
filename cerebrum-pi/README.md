# Cerebrum CM4 Orchestrator Setup Guide

Intelligent code generation system running on Raspberry Pi CM4

## Prerequisite: VPS Backend

The CM4 Orchestrator depends on a running Cerebrum VPS Inference Backend to perform model inference and generate API keys.

Before proceeding, ensure the VPS backend is installed, running, and that you have generated a `CEREBRUM_API_KEY`.

📙 See: [`cerebrum-backend/README.md`](../cerebrum-backend/README.md)

## Architecture

```text
┌──────────────────────────────┐        ┌──────────────────────────────┐
│  CM4 Orchestrator            │        │  VPS Inference Backend       │
│  (FastAPI :7000)             │  SSE   │  (llama.cpp :9000)           │
│                              │ ─────▶ │                              │
│  • Prompt analysis           │        │  • Model execution           │
│  • Chunking & deduplication  │        │  • Token streaming           │
│  • Request routing           │        │  • Resource protection       │
└──────────────────────────────┘        └──────────────────────────────┘
```
## How It Works (Overview)

The CM4 Orchestrator performs intelligent prompt preparation before forwarding requests to the VPS backend, including chunking, deduplication, model routing, and fault protection.

For a detailed breakdown of Cerebrum’s internal design and algorithms, see:

📚 [ARCHITECTURE.md](../docs/architecture/ARCHITECTURE.md)

## Installation

On the Raspberry Pi, clone or sync the Cerebrum repository and install Python dependencies:

```bash
cd /opt/cerebrum-pi
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Quick Start

1. **Configure API Key**
```bash
cd /opt/cerebrum-pi
sudo nano .env
# Add CEREBRUM_API_KEY (from the VPS backend)
# This key must match the `CEREBRUM_API_KEY` you generated on the VPS backend.
```

2. **Start VPS Backend**
```bash
# On VPS
cd ~/cerebrum-backend
./start_vps.sh

# Verify health
curl http://localhost:9000/health
```

3. **Start Server (Orchestrator)**
```bash
# On Raspberry Pi
cd /opt/cerebrum-pi
./start.sh
```

4. **Test**
```bash
cd /opt/cerebrum-pi
./test.sh
```

5. **Launch Streaming REPL**
```bash
cd /opt/cerebrum-pi/scripts
./cerebrum_repl.sh
```

**REPL Commands:**
```bash
>>> :help              Show commands
>>> :model qwen_7b     Switch model
>>> :lang python       Set language
>>> :multi             Toggle multiline mode
>>> def fibonacci(n):  Generate code!
```

## API Endpoints

### Health Check
```bash
curl http://localhost:7000/health
```

### Code Completion (Non-Streaming)
```bash
curl -X POST http://localhost:7000/v1/complete \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "def fibonacci(n):",
    "language": "python",
    "max_tokens": 256
  }'
```
### Code Completion (Streaming)
```bash
curl -N -X POST http://localhost:7000/v1/complete/stream \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "def hello():",
    "language": "python",
    "max_tokens": 128
  }'
```

**Response:** Server-Sent Events (SSE)
> Example output: you should see something like this...
```bash
data: {"token": "import", "total_tokens": 1}
data: {"token": " asyncio", "total_tokens": 2}
...
data: {"done": true, "total_tokens": 129, "inference_time": 182.14}
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

```text
/opt/cerebrum-pi/
├── cerebrum/
│   ├── api/
│   │   ├── main.py                  # Main API server
│   │   ├── middleware
│   │   │   ├── __init__.py
│   │   │   ├── load_shed.py         # Concurrency limiting
│   │   │   ├── log_context.py       # Request logging
│   │   │   └── request_id.py        # UUID correlation
│   │   └── routes
│   │       ├── __init__.py
│   │       ├── _chunking_helper.py  # Smart chunking logic
│   │       ├── health.py            # Health checks
│   │       ├── inference.py         # Streaming endpoints
│   │       ├── models.py            # Model listing
│   │       └── stats.py             # System statistics
│   ├── core/
│   │   └── vps_client.py            # Connection pooling, circuit breaker
│   ├── retrieval/              
│   │   ├── __init__.py
│   │   ├── assembler.py.            # Prompt assembly
│   │   ├── chunker.py               # Text chunking
│   │   ├── instruction_parser.py    # Instruction extraction
│   │   └── ranker.py                # Relevance ranking + dedup
│   └── ...
├── scripts/
│   └── cerebrum_repl.sh             # Interactive streaming CLI
├── .env                             # Configuration
├── start.sh                         # Start server
├── stop.sh                          # Stop server
├── test.sh                          # Full system test
└── test_vps.sh                      # Quick VPS test
```
**Active Components:**
- `api/` - All endpoints, middleware, routing
- `core/` - VPS connection management
- `retrieval/` - Smart chunking and prompt assembly

**Future Expansion:**
- `orchestration/` - Multi-step task coordination
- `reasoning/` - Symbolic / constraint-based reasoning
- `tasks/` - Reusable task templates
- `utils/` - Shared helper functions

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
cat .env | grep CEREBRUM_API_KEY

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
- Debian 12 (Bookworm)
- Python 3.9+
- Network connection to VPS (via Tailscale)

## Performance

- **Local routing:** typically under 10ms
- **VPS inference:** 1-5 seconds (may vary depending on model size and load)
- **Memory usage:** ~500MB (CM4)

## Support

Check VPS backend status:
```bash
ssh unicorn1@173.249.193.188
cd ~/cerebrum-backend
./test.sh
```
