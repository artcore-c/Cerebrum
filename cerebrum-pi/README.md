# Cerebrum CM4 Orchestrator Setup Guide

Intelligent code generation system component running on Raspberry Pi CM4

## Overview

The CM4 Orchestrator transforms a **Raspberry Pi** into an intelligent AI coordination layer. It performs all prompt analysis, context management, and request routing locally, then delegates model execution to the VPS backend. With this distributed approach we create a unique hybrid system that leverages each component’s natural advantages.

**The CM4 Orchestrator provides:**
- **Prompt intelligence** - Extracts instructions, chunks large code, deduplicates patterns
- **Smart routing** - Language-aware model selection (Qwen for Python/JS, CodeLLaMA for Rust/C/C++)  
- **Real-time coordination** - SSE streaming, concurrency limits, request tracking
- **Production resilience** - Circuit breakers, load shedding, correlation IDs

The CM4 handles millisecond-scale decisions and coordination, while the VPS handles second-scale large model inference.

**As part of a Hybrid System the Orchestrator intentionally does not:**
- Run large language models locally
- Perform heavy inference or training
- Store user prompts or responses long-term

Think of it as a smart proxy: it decides *what* to send, *how much* to send, and *how* to stream results back, letting the VPS focus purely on model execution.

## System Requirements

- Raspberry Pi CM4 (4GB+ RAM recommended)
- Debian 12 (Bookworm)
- Python 3.11+
- Network connection to VPS (via Tailscale)

## Performance

- **Local routing:** typically under 10ms
- **VPS inference:** 1-5 seconds (may vary depending on model size and load)
- **Memory usage:** ~500MB (CM4)

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
For more detail about Cerebrum’s internal design and algorithms,

📚 See: [`docs/architecture/ARCHITECTURE.md`](../docs/architecture/ARCHITECTURE.md)

## Prerequisites

The CM4 Orchestrator depends on a running Cerebrum VPS Inference Backend to perform model inference and generate API keys.

You'll need to generate an API key on the VPS before starting the orchestrator, then add it to the `.env` file on the Raspberry Pi. _The orchestrator reads this key at startup to authenticate requests to the VPS._

📙 See: [`cerebrum-backend/README.md`](../cerebrum-backend/README.md)

The CM4 Orchestrator runs inside a Python virtual environment (venv). Dependencies are installed AFTER the venv is activated, and can be installed manually or via requirements.txt (recommended). 
For the full list of dependencies, 

📄 See: [`cerebrum-pi/requirements.txt`](../cerebrum-pi/requirements.txt)

> **Note:** You can complete the Installation steps below without the VPS running, but the orchestrator will not start until the VPS backend is configured and you've added your API key to `.env`.

## Installation

On the Raspberry Pi, clone or sync the Cerebrum repository and install Python dependencies.

1. **Clone Repository**
> **Note:** The Cerebrum repository contains both the CM4 Orchestrator and the VPS backend.  
> These instructions assume you are working from the **CM4 Orchestrator directory** (`cerebrum-pi/`).
```bash
cd /opt
git clone https://github.com/artcore-c/Cerebrum.git
cd Cerebrum/cerebrum-pi
```

2. **Install System Dependencies**
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip
```
3. **Set Up Python Virtual Environment**
```bash
cd /opt/Cerebrum/cerebrum-pi
python3 -m venv .venv
source .venv/bin/activate
```
4. **Install Python Dependencies**
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Quick Start

1. **Configure API Key**

Create the `.env` configuration file with your VPS API key:
```bash
cd /opt/Cerebrum/cerebrum-pi
sudo nano .env
```

Then paste the following, **replacing `Add_Your_API_Key_Here` with the key you generated on the VPS**:
```dotenv
# Cerebrum CM4 Configuration

# VPS Backend Connection (Tailscale)
VPS_ENDPOINT=http://127.0.0.1:9000
VPS_API_KEY=Add_Your_API_Key_Here

# CM4 API Configuration
CEREBRUM_HOST=0.0.0.0
CEREBRUM_PORT=7000

# Logging
LOG_LEVEL=INFO
```
**Save and exit**:

Press `Ctrl+O` to save, then `Enter` to confirm

Press `Ctrl+X` to exit.

**Verify your configuration:**
```bash
cat .env | grep VPS_API_KEY
# Should show: VPS_API_KEY=your_actual_key_here
```
> This must match the key generated on the VPS (where it is defined as CEREBRUM_API_KEY).

2. **Start VPS Backend**
```bash
# SSH into your VPS
ssh <your-vps-user>@<your-vps-host>

# Navigate to the backend directory
cd ~/cerebrum-backend

# Start the backend
./start.sh

# Verify health
curl http://localhost:9000/health
```

3. **Start Server (Orchestrator)**
```bash
# On Raspberry Pi
cd /opt/Cerebrum/cerebrum-pi
./start.sh
```

4. **Test**
```bash
./test.sh
```

5. **Launch Streaming REPL**
```bash
cd /opt/Cerebrum/cerebrum-pi/scripts
./cerebrum_repl.sh
```

> **REPL Commands:**
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

> **Example Response:** Server-Sent Events (SSE)
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

> **Example response:**
```json
{
  "models": [
    {
      "id": "qwen_7b",
      "name": "Qwen 7B",
      "languages": ["python", "javascript", "typescript"]
    },
    {
      "id": "codellama_7b", 
      "name": "CodeLLaMA 7B",
      "languages": ["rust", "c", "cpp", "go"]
    }
  ]
}
```

### System Stats
```bash
curl http://localhost:7000/v1/stats
```

> **Example response:**
```json
{
  "uptime": 3600.5,
  "requests_total": 42,
  "requests_active": 1,
  "vps_available": true,
  "memory_mb": 487.2
}
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
│   │   ├── assembler.py             # Prompt assembly
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

**Future Expansions:**
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
ssh <your-vps-user>@<your-vps-host>
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
ssh <your-vps-user>@<your-vps-host>
cat ~/cerebrum-backend/.env | grep CEREBRUM_API_KEY
```

## Development

**Watch logs:**
```bash
./start.sh
# In another terminal:
tail -f logs/cerebrum.log
```

**By default, logs are written to:**
- `logs/cerebrum.log` – orchestrator runtime logs
- `journalctl` – if running under systemd

If troubleshooting, start here.

**Manual testing:**
```bash
# Quick health check
curl localhost:7000/health | jq

# Test VPS connection
curl localhost:7000/v1/vps/health | jq
```

## Environment Variables (.env)

**Required:**
- `VPS_API_KEY` – must match the API key generated on the VPS backend

**Optional:**
- `VPS_ENDPOINT` – override default backend address

## Support

Check VPS backend status:
```bash
ssh <your-vps-user>@<your-vps-host>
cd ~/cerebrum-backend
./test.sh
```
