# Cerebrum Development Guide

Complete guide for developing, testing, and deploying Cerebrum components.

## Table of Contents

- [Development Environment](#development-environment)
- [Project Structure](#project-structure)
- [Sync Workflow](#sync-workflow)
- [Testing](#testing)
- [Debugging](#debugging)
- [Adding Features](#adding-features)
- [Code Style](#code-style)
- [Common Tasks](#common-tasks)

---

## Development Environment

### macOS Setup (Primary Development Machine)

**Requirements:**
- macOS Monterey or later
- VS Code + VS Code Insider
- Git
- Python 3.11+ (for local testing)
- SSH access to CM4 and VPS

**Initial Setup:**
```bash
# Clone repository
cd ~/
git clone https://github.com/artcore-c/Cerebrum.git
cd Cerebrum

# Install local Python env (optional, for linting)
python3 -m venv .venv
source .venv/bin/activate
pip install -r cerebrum-pi/requirements.txt
pip install -r cerebrum-backend/requirements.txt
```

**VS Code Extensions (Recommended):**
- Python (Microsoft)
- Pylance
- autopep8 or Black (formatting)
- GitLens
- Remote - SSH (for direct editing on Pi/VPS)

---

## Project Structure
```
Cerebrum/                        # Meta-repository (macOS)
│
├── cerebrum-pi/                 # CM4 Orchestrator code
│   ├── cerebrum/                # Python package
│   │   ├── api/                 # FastAPI application
│   │   ├── core/                # VPS client
│   │   └── retrieval/           # Chunking, RAG
│   ├── scripts/                 # Utilities
│   ├── tests/                   # Test suites
│   └── requirements.txt
│
├── cerebrum-backend/            # VPS Backend code
│   ├── vps_server/              # Inference service
│   ├── scripts/                 # Management tools
│   └── requirements.txt
│
├── docs/                        # Documentation
├── scripts/                     # Development tools
│   ├── sync_to_cm4.sh           # Deploy to Raspberry Pi
│   └── sync_to_vps.sh           # Deploy to VPS
│
└── shared/                      # Shared resources
    ├── knowledge_base/
    └── models/
```

### Deployment Targets

| Component | Location | Path |
|-----------|----------|------|
| **CM4 Orchestrator** | Raspberry Pi CM4 | `/opt/cerebrum-pi/` |
| **VPS Backend** | Debian VPS | `~/Cerebrum/cerebrum-backend/` |

---

## Sync Workflow

### Quick Deploy

**Deploy CM4 changes:**
```bash
./scripts/sync_to_cm4.sh
```

**Deploy VPS changes:**
```bash
./scripts/sync_to_vps.sh
```

### What Gets Synced

**CM4 Sync (`sync_to_cm4.sh`):**
```bash
# Syncs:
cerebrum-pi/cerebrum/          # Python code
cerebrum-pi/scripts/           # Utilities
cerebrum-pi/requirements.txt
cerebrum-pi/.env              # If exists locally

# Excludes:
__pycache__/
*.pyc
.venv/
logs/
```

**VPS Sync (`sync_to_vps.sh`):**
```bash
# Syncs:
cerebrum-backend/vps_server/
cerebrum-backend/scripts/
cerebrum-backend/requirements.txt
cerebrum-backend/.env         # If exists locally

# Excludes:
__pycache__/
*.pyc
.venv/
logs/
models/                       # Too large, managed separately
```

### Manual Sync (Alternative)

**CM4:**
```bash
rsync -avz --exclude='__pycache__' --exclude='.venv' \
  ~/Cerebrum/cerebrum-pi/ \
  kali@100.75.37.26:/opt/cerebrum-pi/
```

**VPS:**
```bash
rsync -avz --exclude='__pycache__' --exclude='.venv' --exclude='models' \
  ~/Cerebrum/cerebrum-backend/ \
  unicorn1@100.78.22.113:~/Cerebrum/cerebrum-backend/
```

---

## Testing

### Local Testing (macOS)

**Syntax/Import Checks:**
```bash
# Test CM4 code
cd ~/Cerebrum/cerebrum-pi
python -m py_compile cerebrum/api/main.py
python -m py_compile cerebrum/retrieval/chunker.py

# Test VPS code
cd ~/Cerebrum/cerebrum-backend
python -m py_compile vps_server/main.py
```

**Unit Tests (if available):**
```bash
cd ~/Cerebrum/cerebrum-pi
pytest tests/
```

### CM4 Testing (On Device)

**SSH into CM4:**
```bash
ssh kali@100.75.37.26
```

**Full System Test:**
```bash
cd /opt/cerebrum-pi
./test.sh
```

**Expected output:**
```
Testing CM4 Orchestrator...
✓ Health check passed
✓ VPS connection established
✓ Model listing successful
✓ Inference endpoint responding
All tests passed!
```

**Quick VPS Connection Test:**
```bash
cd /opt/cerebrum-pi
./test_vps.sh
```

**Manual API Test:**
```bash
# Health check
curl http://localhost:7000/health | jq

# Simple completion
curl -X POST http://localhost:7000/v1/complete \
  -H "Content-Type: application/json" \
  -d '{"prompt": "def hello():", "language": "python", "max_tokens": 32}' | jq
```

**Watch Logs:**
```bash
tail -f logs/cerebrum.log
```

### VPS Testing (On Server)

**SSH into VPS:**
```bash
ssh unicorn1@100.78.22.113
```

**Full System Test:**
```bash
cd ~/Cerebrum/cerebrum-backend
./test.sh
```

**Expected output:**
```
Testing VPS Backend...
✓ Health check passed
✓ Model paths verified
✓ Inference endpoint responding
✓ Authentication working
All tests passed!
```

**Manual API Test:**
```bash
# Health check (no auth)
curl http://127.0.0.1:9000/health | jq

# Model list (requires auth)
curl -H "X-API-Key: $(grep CEREBRUM_API_KEY .env | cut -d= -f2)" \
  http://127.0.0.1:9000/v1/models | jq
```

**Watch Logs:**
```bash
# If using start.sh
tail -f logs/backend.log

# If using systemd
sudo journalctl -u cerebrum-backend -f
```

---

## Debugging

### Common Issues

**CM4: "Can't connect to VPS"**
```bash
# Check Tailscale
ssh kali@100.75.37.26
sudo tailscale status

# Test VPS directly
./test_vps.sh

# Check VPS is running
ssh unicorn1@100.78.22.113
cd ~/Cerebrum/cerebrum-backend
ps aux | grep uvicorn
```

**CM4: "Port already in use"**
```bash
ssh kali@100.75.37.26
sudo lsof -i :7000
# Kill process if needed
kill <PID>
```

**VPS: "Model not found"**
```bash
ssh unicorn1@100.78.22.113

# Verify model paths in code
grep "model_paths" ~/Cerebrum/cerebrum-backend/vps_server/main.py

# Check files exist
ls -lh ~/Cerebrum/cerebrum-backend/models/
```

**VPS: "Out of memory"**
```bash
ssh unicorn1@100.78.22.113

# Check memory
free -h

# Unload models manually
curl -X POST -H "X-API-Key: $(grep CEREBRUM_API_KEY .env | cut -d= -f2)" \
  http://127.0.0.1:9000/v1/cleanup
```

### Debug Logging

**Enable verbose logging:**

Edit `.env` on CM4:
```bash
LOG_LEVEL=DEBUG
```

Restart:
```bash
./stop.sh
./start.sh
```

Watch detailed logs:
```bash
tail -f logs/cerebrum.log
```

### Request Tracing

Every request gets a UUID for end-to-end tracking:

**CM4 logs:**
```
[65652caa-c647-4685-be81-5e51bc97f453] POST /v1/complete/stream 200 182.14s
```

**VPS logs:**
```
[65652caa-c647-4685-be81-5e51bc97f453] Model inference: qwen_7b, 129 tokens
```

Search logs by request ID:
```bash
grep "65652caa-c647-4685-be81-5e51bc97f453" logs/cerebrum.log
```

---

## Adding Features

### Workflow

1. **Branch (optional):**
```bash
   git checkout -b feature/new-chunking-algo
```

2. **Edit on macOS:**
```bash
   code ~/Cerebrum/cerebrum-pi/cerebrum/retrieval/chunker.py
```

3. **Local syntax check:**
```bash
   python -m py_compile cerebrum/retrieval/chunker.py
```

4. **Sync to CM4:**
```bash
   ./scripts/sync_to_cm4.sh
```

5. **Test on device:**
```bash
   ssh kali@100.75.37.26
   cd /opt/cerebrum-pi
   ./test.sh
```

6. **Iterate until working**

7. **Commit:**
```bash
   git add cerebrum-pi/cerebrum/retrieval/chunker.py
   git commit -m "feat: improve chunking deduplication algorithm"
   git push origin feature/new-chunking-algo
```

### Example: Adding a New Endpoint

**1. Define route** (`cerebrum-pi/cerebrum/api/routes/inference.py`):
```python
@router.post("/v1/explain")
async def explain_code(request: ExplainRequest):
    """Explain what code does"""
    # Implementation
    pass
```

**2. Add schema** (`cerebrum-pi/cerebrum/api/schemas/`):
```python
class ExplainRequest(BaseModel):
    code: str
    language: str
```

**3. Test locally:**
```bash
python -m py_compile cerebrum/api/routes/inference.py
```

**4. Sync and test:**
```bash
./scripts/sync_to_cm4.sh
ssh kali@100.75.37.26
cd /opt/cerebrum-pi
./stop.sh && ./start.sh
curl -X POST http://localhost:7000/v1/explain \
  -H "Content-Type: application/json" \
  -d '{"code": "def fib(n): ...", "language": "python"}'
```

**5. Document** (update `docs/api/API.md`)

---

## Code Style

### Python Guidelines

**Follow PEP 8:**
```bash
# Format with autopep8
autopep8 --in-place --aggressive cerebrum/api/main.py

# Or Black (opinionated)
black cerebrum/
```

**Type hints (preferred):**
```python
def chunk_text(text: str, max_size: int = 1000) -> List[str]:
    """Chunk text into blocks"""
    pass
```

**Docstrings:**
```python
def extract_instruction(prompt: str) -> tuple[str, str]:
    """Extract instruction from prompt.
    
    Args:
        prompt: Full prompt text
        
    Returns:
        Tuple of (code, instruction)
    """
    pass
```

### Project Conventions

**File naming:**
- Modules: `snake_case.py`
- Classes: `PascalCase`
- Functions: `snake_case()`

**Import order:**
```python
# Standard library
import os
import sys

# Third-party
from fastapi import FastAPI
import httpx

# Local
from cerebrum.core.vps_client import VPSClient
```

**Constants:**
```python
MAX_CONCURRENT_REQUESTS = 2
VPS_ENDPOINT = "http://127.0.0.1:9000"
```

---

## Common Tasks

### Update Dependencies

**CM4:**
```bash
# Edit requirements.txt locally
vim ~/Cerebrum/cerebrum-pi/requirements.txt

# Sync
./scripts/sync_to_cm4.sh

# Install on CM4
ssh kali@100.75.37.26
cd /opt/cerebrum-pi
source .venv/bin/activate
pip install -r requirements.txt
./stop.sh && ./start.sh
```

**VPS:**
```bash
# Same process for cerebrum-backend/requirements.txt
./scripts/sync_to_vps.sh
ssh unicorn1@100.78.22.113
cd ~/Cerebrum/cerebrum-backend
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart cerebrum-backend
```

### Add a New Model

**1. Download model to VPS:**
```bash
ssh unicorn1@100.78.22.113
cd ~/Cerebrum/cerebrum-backend/models/
wget https://huggingface.co/.../model.gguf
```

**2. Update model map** (`vps_server/main.py`):
```python
model_paths = {
    "qwen_7b": "/home/unicorn1/Cerebrum/cerebrum-backend/models/qwen-7b-q4.gguf",
    "new_model": "/home/unicorn1/Cerebrum/cerebrum-backend/models/model.gguf",  # ADD THIS
}
```

**3. Restart VPS:**
```bash
sudo systemctl restart cerebrum-backend
```

**4. Update CM4 routing** (`cerebrum-pi/cerebrum/api/routes/_chunking_helper.py`):
```python
_MODEL_MAP = {
    "python": "qwen_7b",
    "haskell": "new_model",  # ADD THIS
}
```

**5. Sync and restart CM4:**
```bash
./scripts/sync_to_cm4.sh
ssh kali@100.75.37.26
cd /opt/cerebrum-pi
./stop.sh && ./start.sh
```

### Regenerate API Key

**On VPS:**
```bash
ssh unicorn1@100.78.22.113
cd ~/Cerebrum/cerebrum-backend/scripts
./generate_api_key.sh
# Copy new key
```

**Update CM4 `.env`:**
```bash
ssh kali@100.75.37.26
nano /opt/cerebrum-pi/.env
# Paste new CEREBRUM_API_KEY
```

**Restart both:**
```bash
# VPS
sudo systemctl restart cerebrum-backend

# CM4
cd /opt/cerebrum-pi
./stop.sh && ./start.sh
```

---

## Performance Profiling

### CM4 Overhead Measurement
```bash
ssh kali@100.75.37.26
cd /opt/cerebrum-pi

# Time a simple request
time curl -X POST http://localhost:7000/v1/complete \
  -H "Content-Type: application/json" \
  -d '{"prompt": "def test():", "language": "python", "max_tokens": 32}'
```

Check logs for breakdown:
```
Chunking large prompt: 50ms
VPS request: 15.2s
Total: 15.25s
```

### VPS Resource Monitoring
```bash
ssh unicorn1@100.78.22.113

# Watch resources during inference
watch 'curl -s http://127.0.0.1:9000/health | jq'

# System stats
htop
```

---

## Git Workflow

### Branching Strategy
```
main            - Production-ready code
├── dev         - Integration branch
└── feature/*   - New features
└── fix/*       - Bug fixes
```

### Commit Messages
```
feat: add semantic search with FAISS
fix: resolve circuit breaker timeout issue
docs: update API reference for /v1/explain
refactor: extract chunking helper logic
test: add unit tests for instruction parser
```

### Before Committing
```bash
# Run tests
cd ~/Cerebrum/cerebrum-pi
pytest tests/

# Check syntax
python -m py_compile cerebrum/**/*.py

# Format code
black cerebrum/

# Commit
git add .
git commit -m "feat: improve chunking algorithm"
git push
```

---

## Troubleshooting Development Issues

### "rsync: command not found"
```bash
# Install on macOS
brew install rsync
```

### "Permission denied" on sync
```bash
# Fix CM4 permissions
ssh kali@100.75.37.26
sudo chown -R kali:kali /opt/cerebrum-pi
```

### Python import errors after sync
```bash
# Reinstall dependencies
ssh kali@100.75.37.26
cd /opt/cerebrum-pi
source .venv/bin/activate
pip install --force-reinstall -r requirements.txt
```

### Can't SSH to CM4/VPS
```bash
# Check Tailscale
tailscale status

# Use IP instead
ssh kali@100.75.37.26
ssh unicorn1@100.78.22.113
```

---

## Best Practices

1. **Always test locally first** (syntax checks)
2. **Sync incrementally** (one component at a time)
3. **Watch logs during testing** (`tail -f logs/`)
4. **Use request IDs for debugging** (grep by UUID)
5. **Keep .env files in sync** (CM4 ↔ VPS API keys must match)
6. **Don't sync models** (too large, manage separately)
7. **Restart services after config changes**
8. **Document breaking changes** (update API.md)
9. **Test on actual hardware** (Mac ≠ ARM CM4)
10. **Commit working code only** (test before push)

---

## Resources

- **Main README:** [`/README.md`](../../README.md)
- **API Reference:** [`/docs/api/API.md`](../api/API.md)
- **Architecture:** [`/docs/architecture/ARCHITECTURE.md`](../architecture/ARCHITECTURE.md)
- **CM4 Setup:** [`/cerebrum-pi/README.md`](../../cerebrum-pi/README.md)
- **VPS Setup:** [`/cerebrum-backend/README.md`](../../cerebrum-backend/README.md)

---

**Questions? Open an issue or discussion on GitHub!**