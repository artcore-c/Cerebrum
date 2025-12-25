# Cerebrum VPS Backend

Lightweight inference backend for heavy model computation, designed to run on a VPS and serve streamed responses to a remote orchestrator.

This service is intended to be accessed only by trusted clients (e.g. the Cerebrum orchestrator) over a private network such as Tailscale.

## Overview

The Cerebrum VPS Backend runs on a virtual private server and is responsible for all large language model inference. It is designed to be accessed remotely by the CM4 Orchestrator over a private network (such as Tailscale) and is not intended to be exposed publicly.

All commands in this guide are assumed to be run **on the VPS itself**, either via SSH or a remote console.

## Accessing the VPS

You’ll need SSH access (or remote management via a web console if your VPS provides it) to your VPS for the installation, configuration, and management of the Cerebrum VPS backend service.

Typical usage:
```bash
ssh <your-vps-user>@<your-vps-host>
```
> **Note:** If you are using **Tailscale** (recommended), you can use SSH with your VPS’s Tailscale hostname or IP.

## Installation

On the VPS, clone the Cerebrum repository and switch to the `cerebrum-backend/` directory.

1. **Clone Repository**
> **Note:** The Cerebrum repository contains both the CM4 Orchestrator and the VPS backend.  
> These instructions assume you are working from the **VPS Backend directory** (`cerebrum-backend/`).
```bash
cd ~
git clone https://github.com/artcore-c/Cerebrum.git
cd Cerebrum/cerebrum-backend
```

2. **Install System Dependencies**
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip
```
3. **Set Up Python Virtual Environment**
```bash
cd ~/Cerebrum/cerebrum-backend
python3 -m venv .venv
source .venv/bin/activate
```
4. **Install Python Dependencies**
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```
## Model Installation

The Cerebrum VPS Backend uses **prebuilt GGUF models** stored locally on the VPS.  
Models are **not downloaded or built automatically** at runtime.

When you clone the Cerebrum repository, the backend expects model files to reside in the `cerebrum-backend/models/` directory.

Models are loaded on-demand when requested by the CM4 Orchestrator and cached in RAM until they are unloaded or become idle.

### Supported Models

Cerebrum is designed to work with `llama.cpp`-compatible GGUF models.  
The repository is commonly used with models such as:

- Qwen 7B (quantized)
- CodeLLaMA 7B / 13B (quantized)
- WizardCoder
- DeepSeek

> **Note:** While exact model selection(s) should be in consideration of intended use, it's also recommended they prioritize selections depending on available system resources.

### Model Paths (Important)

Model file paths are defined directly in the `cerebrum-backend/` VPS code in the file `vps_server/main.py`:

📄 see: [`cerebrum-backend/vps_server/main.py`](../cerebrum-backend/vps_server/main.py)

Each model name is mapped to an absolute filesystem path. For example:
```bash
model_paths = {
    "qwen_7b": "/home/<vps-user>/cerebrum-backend/models/qwen-7b-q4.gguf",
    "codellama_7b": "/home/<vps-user>/cerebrum-backend/models/codellama-7b-q4.gguf",
}
```
You **must update these paths** to match:
- your VPS username
- the actual location of the model files

This explicit mapping keeps model loading predictable and avoids accidental exposure of arbitrary filesystem paths.
> **Note:** The placeholder `<vps-user>` should be replaced with your actual VPS username (e.g. `ubuntu`, `debian`, or another user you created).

## Quick Start

1. **Generate API Key**
```bash
cd ~/Cerebrum/cerebrum-backend/scripts
./generate_api_key.sh
```

2. **Configure .env**

The backend is configured via a `.env` file located in the `cerebrum-backend/` directory.

**Create or edit the file**:
```bash
cd ~/Cerebrum/cerebrum-backend
sudo nano .env
```

Edit `.env`:
- `CEREBRUM_API_KEY` - API authentication key
- `CEREBRUM_N_THREADS=1` - Number of CPU threads allocated to model inference
- `VPS_BIND_IP` - Local Host (127.0.0.1)
- `CEREBRUM_VPS_PORT` - Port (9000)
- `MAX_CPU_PERCENT` - Max CPU before rejecting requests (70)

```bash
# VPS Configuration
# Cerebrum VPS Backend - Example Configuration
# Copy to .env and adjust as needed

# Authentication
CEREBRUM_API_KEY=your-api-key-here

# Advanced users may increase this value on higher-core VPS instances, but doing so will increase CPU usage proportionally.
CEREBRUM_N_THREADS=1

# Network (bind locally; access via tunnel or Tailscale)
VPS_BIND_IP=127.0.0.1
CEREBRUM_VPS_PORT=9000

# Resource limits
MAX_CPU_PERCENT=70

# Optional hardening: allow only a specific client IP
# ALLOWED_CM4_IP=100.x.y.z
```
**Verify configuration**:
```bash
grep CEREBRUM_API_KEY .env
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
> Once enabled, the backend will start automatically on reboot.

## API Endpoints

- `GET /health` - Health check (no auth)
- `POST /v1/inference` - Internal inference endpoint used by the CM4 orchestrator
 (requires API key)
- `GET /v1/models` - List models (requires API key)
- `GET /v1/stats` - System statistics (requires API key)
- `POST /v1/unload/{model}` - Unload model (requires API key)


## Model Management

Models are cached in RAM after first use. They auto-unload after 60 minutes of inactivity.

**Manual cleanup:**
```bash
curl -X POST -H "X-API-Key: YOUR_KEY" http://127.0.0.1:9000/v1/cleanup
```

## Monitoring

Logs are written locally to the `logs/` directory unless overridden by systemd.

```bash
# Watch system resources
watch 'curl -s http://127.0.0.1:9000/health | jq'

# Check stats
curl -H "X-API-Key: YOUR_KEY" http://127.0.0.1:9000/v1/stats | jq
```

## Security

- API key authentication required for all inference endpoints
- Health endpoint is public (for monitoring)
- Intended to bind only to localhost or a private interface (e.g. Tailscale)
- Not designed to be exposed to the public internet

## Resource Protection

- Automatically rejects requests when CPU > 70%
- Automatically rejects when RAM < 1GB available
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
