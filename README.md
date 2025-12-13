# Cerebrum AI

Hybrid AI system optimized for Raspberry Pi CM4 + VPS architecture.

<p align="center">
  <img src="docs/CerebrumGUI-(SSH).png" alt="Cerebrum GUI (SSH)" width="400"/>
</p>

## Architecture

```
┌─────────────────────────────────┐
│  CM4 (Lightweight Orchestrator) │
│  - FastAPI server               │
│  - Request routing              │
│  - Symbolic reasoning (Z3)      │
│  - RAG/retrieval (FAISS)        │
└────────────┬────────────────────┘
             │ HTTP/Tailscale
             │ Port 7000 → 9000
┌────────────▼────────────────────┐
│  VPS (Heavy Inference Backend)  │
│  - Model loading (llama.cpp)    │
│  - Large model inference        │
│  - GPU/CPU optimization         │
└─────────────────────────────────┘
```

## Project Structure

- **cm4/** - Raspberry Pi CM4 code (orchestrator)
- **vps/** - VPS backend code (inference)
- **shared/** - Shared resources (models, knowledge base)
- **docs/** - Documentation
- **deployment/** - Deployment scripts

## Quick Start

### CM4 Setup
```bash
cd cm4
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
./start.sh
```

### VPS Setup
```bash
cd vps
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
./start.sh
```

## Development Workflow

1. **Edit on Mac** - Use VS Code to edit files
2. **Sync to CM4** - `rsync` or `scp` to Raspberry Pi
3. **Sync to VPS** - `rsync` or `scp` to VPS server
4. **Test** - Run tests on both systems

## Components

### CM4 (Port 7000)
- Lightweight orchestration
- API endpoints
- Request routing
- Symbolic reasoning (Z3)
- Vector search (FAISS)

### VPS (Port 9000)
- Heavy model inference
- Model caching
- Resource management
- iOS backend protection

## Documentation

See `docs/` directory for detailed documentation:
- Architecture diagrams
- API reference
- Deployment guides
- Performance optimization

## License

MIT
