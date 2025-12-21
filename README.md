# Cerebrum Interactive AI Code Generation Shell

Hybrid AI system optimized for Raspberry Pi CM4 + VPS architecture.

<p align="center">
  <img src="docs/images/CerebrumGUI-(SSH).png" alt="Cerebrum GUI (SSH)" width="400"/>
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
│  - Model loading eg.(llama.cpp) │
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

## Deployment & Operation

Cerebrum is composed of two independently deployed components:

### 🔹 CM4 Orchestrator (Raspberry Pi)

**Handles request routing, lightweight reasoning, and VPS coordination**

### Deployment:  
[`cerebrum-pi/README.md`](./cerebrum-pi/README.md)

---

### 🔹 VPS Inference Backend

**Runs heavy LLM inference using `llama.cpp` with strict resource controls**
- The backend supports multiple GGUF models via llama.cpp-compatible runtimes
- Models are selected dynamically at request time

### Deployment:  
[`cerebrum-backend/README.md`](./cerebrum-backend/README.md)

---

**Note:**  
The root of this repository is **not directly executable**.  
All runtime instructions live in the component-specific READMEs above.

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
- Multi-model GGUF support (e.g. Qwen, CodeLLaMA, DeepSeek)
- llama.cpp-compatible backends
- Model caching and lifecycle control
- Resource management and isolation

## Documentation

See `docs/` directory for detailed information:
- [Architecture](./docs/architecture/Architecture.md)
- [API Reference](./docs/api/API.md)
- [Optimization](./docs/optimization/PERFORMANCE.md)

## License

This project is licensed under the [MIT License](./LICENSE).
