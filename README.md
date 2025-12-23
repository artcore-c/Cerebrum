# Cerebrum™ - Distributed AI Code Assistant

Token-streaming code generation optimized for edge + cloud architecture

<p align="center">
  <img src="docs/images/CerebrumGUI-(SSH).png" alt="Cerebrum GUI (SSH)" width="400"/>
</p>

## What Makes Cerebrum Unique

## Architecture
```
┌─────────────────────────────────────────────────────────┐
│  Raspberry Pi CM4 (Orchestrator)                        │
│  ┌───────────────────────────────────────────────────┐  │
│  │  FastAPI Server (Port 7000)                       │  │
│  │  • Instruction extraction & prompt assembly       │  │
│  │  • Smart chunking (1000 char blocks, 150 overlap) │  │
│  │  • Deduplication (hash-based fingerprinting)      │  │
│  │  • Load shedding (max 2 concurrent requests)      │  │
│  │  • Request tracking (UUID correlation)            │  │
│  └───────────────────────────────────────────────────┘  │
└───────────────────┬─────────────────────────────────────┘
                    │
                    │ HTTP/Tailscale (Streaming SSE)
                    │ Chunked prompts → Token stream
                    │
┌───────────────────▼─────────────────────────────────────┐
│  VPS Inference Backend (Port 9000)                      │
│  ┌───────────────────────────────────────────────────┐  │
│  │  llama.cpp Runtime                                │  │
│  │  • Model: qwen-7b-q4.gguf / codellama-7b-q4.gguf  │  │
│  │  • Inference: ~1.6 tok/s (CPU, single-threaded)   │  │
│  │  • Connection pool: Persistent httpx client       │  │
│  │  • Circuit breaker: 10s cooldown on failures      │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```
Data Flow:

1. User prompt → CM4 extracts instructions
2. CM4 chunks large code (if >1500 chars)
3. CM4 deduplicates repeated patterns
4. CM4 selects top 3 relevant chunks
5. CM4 assembles instruction-first prompt
6. VPS streams tokens back via SSE
7. CM4 proxies stream to client in real-time

---
## Real-World Performance
### Streaming Inference:
Small prompts (<100 chars): ~17s for 33 tokens (1.9 tok/s)
Large prompts (8KB): ~182s for 129 tokens (0.7 tok/s) after 62% chunking reduction
CM4 overhead: <100ms for chunking + routing

### Context Management:
Input: 8,344 chars (repeated synchronous code)
After chunking: 3,167 chars (62% reduction)
Result: Actual async/await refactored code (not TODO lists!)

### Resource Protection:
Max concurrent: 2 requests (load shedding)
Circuit breaker: 10s cooldown after VPS failures
Request timeout: Configurable per endpoint
Connection pooling: Persistent HTTP client (no repeated initialization)

---
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
