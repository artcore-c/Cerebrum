# Cerebrum/docs/architecture/Architecture.md

## System Overview

```
┌──────────────────────────────────────────┐
│           User Interface/IDE             │
└─────────────────────────┬────────────────┘
                          │
                ┌─────────▼──────────┐
                │  CM4 Orchestrator  │
                │  Port 7000         │
                └───┬────────────┬───┘
                    │            │
┌───────────────────▼────┐   ┌───▼────────────┐
│ Local Orchestration    │   │ HTTP/Tailscale │
│ - Request analysis     │   └───┬────────────┘
│ - Chunking & filtering │       │                 
│ - Routing logic        │       │
└────────────────────────┘       │    
                                 │
                                 │
                  ┌──────────────▼──────┐
                  │   VPS Backend       │
                  │   Port 9000         │
                  │   - llama.cpp       │
                  │   - Model loading   │
                  │   - Heavy inference │
                  └─────────────────────┘
```

## Component Responsibilities

### CM4 (Raspberry Pi)
- **Role:** Lightweight orchestrator
- **Resources:** 4GB RAM, 78GB storage
- **Tasks:**
  - API server (FastAPI)
  - Request routing
  - Symbolic reasoning (Z3)
  - Vector search (FAISS)
  - Result and response caching
  
### VPS (Debian Server)
- **Role:** Heavy inference backend
- **Resources:** 7.26GB RAM, fast CPU
- **Tasks:**
  - Backend isolation from direct client access
  - Model loading (llama.cpp)
  - Large model inference
  - Model caching

## Data Flow

1. User sends request → CM4:7000
2. CM4 analyzes request complexity and intent
3. If simple: Local processing (Z3/FAISS)
4. If complex: Forward to VPS:9000
5. VPS loads model, runs inference
6. VPS returns result → CM4
7. CM4 returns to user

## Network

- **CM4 ↔ VPS:** Tailscale (encrypted)
- **CM4 External:** Port 7000
- **VPS Internal:** Port 9000 (not public)
- **Protocol:** HTTP/JSON (SSE for streaming)

## Security

- API key authentication
- Tailscale encryption
- VPS not exposed to internet
- Rate limiting on CM4
