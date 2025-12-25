# Cerebrum VPS Backend

High-performance inference engine for heavy model computation in the Cerebrum distributed AI code generation system

## Overview

The Cerebrum VPS Backend transforms a budget VPS into a dedicated AI inference server. It handles all heavy model computation while the CM4 Orchestrator manages routing, context, and coordination. Designed for private network access (Tailscale recommended), this backend focuses exclusively on one task: fast, efficient token generation.

**Core capabilities:**
- Stream-optimized inference via llama.cpp
- On-demand model loading and automatic unloading
- Built-in resource protection (CPU/RAM limits)
- API key authentication for trusted clients only

Think of it as the computational workhorse, no UI, no complexity, just reliable model execution accessible only to your orchestrator.

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

Models are loaded into memory on-demand when first requested by the CM4 Orchestrator, then cached until unloaded or idle.

### Supported Models

Cerebrum is designed to work with `llama.cpp`-compatible GGUF models.  
The repository is commonly used with models such as:

- Qwen 7B (quantized)
- CodeLLaMA 7B / 13B (quantized)
- WizardCoder
- DeepSeek

> **Note:** While exact model selection(s) should be in consideration of intended use, it's also recommended they prioritize selections depending on available system resources. A good practice would be to order your models starting with your top picks first. 

### Model Paths (Important)

Model file paths are defined directly in the `cerebrum-backend/` VPS code in the file `vps_server/main.py`:

📄 see: [`cerebrum-backend/vps_server/main.py`](../cerebrum-backend/vps_server/main.py)

Each model name is mapped to an absolute filesystem path. For example:
```bash
model_paths = {
    "qwen_7b": "/home/<vps-user-name>/Cerebrum/cerebrum-backend/models/qwen-7b-q4.gguf",
    "codellama_7b": "/home/<vps-user-name>/Cerebrum/cerebrum-backend/models/codellama-7b-q4.gguf",
}
```
> **Note:** In the file `vps_server/main.py` the placeholder `<vps-user-name>` should be replaced with your actual VPS username (e.g. `debian`, or another username you created).

You **must update these paths** to match:
- your VPS username
- the actual location of the model files

This explicit mapping keeps model loading predictable and avoids accidental exposure of arbitrary filesystem paths.

### Expected Directory Layout

After cloning the repository, your backend directory should look like this:

```text
cerebrum-backend/
├── models/
│   ├── qwen-7b-q4.gguf
│   ├── codellama-7b-q4.gguf
│   └── ...
├── vps_server/
│   └── main.py
├── scripts/
├── start.sh
└── .env
```

## 🚀 Quick Start

1. **Generate API Key**
```bash
cd ~/Cerebrum/cerebrum-backend/scripts
./generate_api_key.sh
```

2. **Configure .env**

The backend is configured via a `.env` file located in the `cerebrum-backend/` directory.

**This example shows the values you'll need to add when you edit** `.env`:
- `CEREBRUM_API_KEY=` API authentication key (Your_API_Key)
- `CEREBRUM_N_THREADS=` Number of CPU threads allocated per inference request (1)
- `VPS_BIND_IP=` Local Host (127.0.0.1)
- `CEREBRUM_VPS_PORT=` Port (9000)
- `MAX_CPU_PERCENT=` Max CPU before rejecting requests (70)

**Create or edit the file**: `.env`
```bash
cd ~/Cerebrum/cerebrum-backend
sudo nano .env
```
**copy the following and paste into** `.env`**, then add your API Key**
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
**Save and exit**:

Press `Ctrl+O` to save, then `Enter` to confirm

Press `Ctrl+X` to exit.

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

## Systemd Service Configuration

**Create or edit the file**: `cerebrum-backend.service`
```bash
cd ~/Cerebrum/cerebrum-backend
sudo nano ~/Cerebrum/cerebrum-backend/cerebrum-backend.service
```
**copy the following and paste into** `cerebrum-backend.service`**, replacing `<vps-user-name>` with your actual VPS username

```bash
[Unit]
Description=Cerebrum VPS Backend
After=network.target

[Service]
CPUQuota=95%
Nice=10
TasksMax=50
MemoryHigh=6000M
MemoryMax=6500M
OOMPolicy=stop

Type=simple
User=<vps-user-name>
WorkingDirectory=/home/<vps-user-name>/Cerebrum/cerebrum-backend
Environment="PATH=/home/<vps-user-name>/Cerebrum/cerebrum-backend/venv/bin"
EnvironmentFile=/home/<vps-user-name>/Cerebrum/cerebrum-backend/.env

ExecStart=/home/<vps-user-name>/Cerebrum/cerebrum-backend/venv/bin/uvicorn \
  vps_server.main:app \
  --host ${VPS_BIND_IP} \
  --port ${CEREBRUM_VPS_PORT} \
  --workers 1

Restart=on-failure
RestartSec=5
StandardOutput=append:/home/<vps-user-name>/Cerebrum/cerebrum-backend/logs/backend.log
StandardError=append:/home/<vps-user-name>/Cerebrum/cerebrum-backend/logs/error.log

[Install]
WantedBy=multi-user.target
```

**Save and exit**:

Press `Ctrl+O` to save, then `Enter` to confirm

Press `Ctrl+X` to exit.

**Verify configuration**:

```bash
cat ~/Cerebrum/cerebrum-backend/cerebrum-backend.service
```

## Enabling the Systemd Service

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

### Authentication

Authenticated requests must include the API key as an HTTP header:

```bash
-H "X-API-Key: YOUR_API_KEY"
```

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

This service is intended to be accessed only by trusted clients (e.g. the Cerebrum orchestrator) over a private network such as Tailscale.

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

---

## What's Next?

With the VPS backend running, you're ready to set up the CM4 Orchestrator:

📘 **CM4 Setup Guide:** [`cerebrum-pi/README.md`](../cerebrum-pi/README.md)

The orchestrator handles all user interaction, prompt preparation, and request coordination—transforming your Raspberry Pi into an intelligent AI control plane powered by this backend.
