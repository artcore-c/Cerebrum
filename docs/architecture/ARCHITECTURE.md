# Cerebrum Architecture

## System Overview
```
┌──────────────────────────────────────────┐
│      User (CLI/API/REPL)                 │
└─────────────────────────┬────────────────┘
                          │
                ┌─────────▼──────────┐
                │  CM4 Orchestrator  │
                │  FastAPI :7000     │
                └───┬────────────┬───┘
                    │            │
┌───────────────────▼────┐   ┌───▼────────────────┐
│ Prompt Preparation     │   │ VPS Communication  │
│ • Instruction extract  │   │ • HTTP/Tailscale   │
│ • Smart chunking       │   │ • Circuit breaker  │
│ • Deduplication        │   │ • Connection pool  │
│ • Model routing        │   │ • SSE streaming    │
└────────────────────────┘   └───┬────────────────┘
                                 │
                  ┌──────────────▼──────────────┐
                  │   VPS Inference Backend     │
                  │   llama.cpp :9000           │
                  │   • On-demand model loading │
                  │   • Token streaming         │
                  │   • Resource protection     │
                  └─────────────────────────────┘
```

## Component Responsibilities

### CM4 Orchestrator (Raspberry Pi)
**Role:** Intelligent coordination and prompt optimization  
**Hardware:** Raspberry Pi CM4, 4GB RAM  
**Stack:** FastAPI, Python 3.11+, httpx

**Active Components:**
- **API Server** - FastAPI with middleware (request_id, log_context, load_shed)
- **Prompt Intelligence** - Instruction extraction, smart chunking (1000 char blocks, 150 overlap)
- **Context Optimization** - Deduplication (hash-based fingerprinting), top-k chunk selection
- **Model Routing** - Language-aware selection (Qwen for Python/JS, CodeLLaMA for Rust/C)
- **Fault Protection** - Circuit breakers (10s cooldown), load shedding (max 2 concurrent)
- **Streaming Coordination** - Real-time SSE proxying, request correlation

**Future Expansion:**
- Vector search (FAISS)
- Retrieval augmentation 
- Multi-step task orchestration
- AST-based chunking

### VPS Inference Backend
**Role:** Heavy model computation  
**Hardware:** Budget VPS, 4GB+ RAM recommended  
**Stack:** FastAPI, llama.cpp (Python bindings)

**Active Components:**
- **Model Execution** - llama.cpp runtime, GGUF model support
- **Resource Management** - On-demand loading, auto-unload after 60min idle
- **Protection** - CPU limit (70%), RAM limit (1GB minimum), request rejection
- **Streaming** - Token-by-token SSE responses

## Data Flow (Detailed)

### Request Processing Pipeline
```
1. User Request
   ↓
2. CM4: Middleware Stack
   • Generate request UUID
   • Log context creation
   • Check concurrent limit (max 2)
   ↓
3. CM4: Prompt Analysis
   • Extract instruction (if present)
   • Check prompt size (>1500 chars?)
   ↓
4. CM4: Smart Chunking (if needed)
   • Split into 1000-char blocks (150 overlap)
   • Deduplicate repeated patterns
   • Rank by relevance to instruction
   • Select top 3 chunks
   • Assemble instruction-first prompt
   • Skip if <10% size reduction
   ↓
5. CM4: Model Selection
   • Map language → model (Qwen/CodeLLaMA)
   ↓
6. CM4 → VPS: HTTP Request
   • Connection pool (persistent httpx)
   • Circuit breaker check
   • Stream request via SSE
   ↓
7. VPS: Model Inference
   • Load model (if not cached)
   • Generate tokens via llama.cpp
   • Stream back via SSE
   ↓
8. CM4: Stream Proxy
   • Forward tokens to client
   • Track total_tokens
   • Log completion
   ↓
9. User: Receives Response
```

### Example: Large Prompt Optimization

**Input:** 8,344 chars (repeated synchronous code + refactoring instruction)
```
CM4 Processing:
1. Extract instruction: "Refactor this to use async/await"
2. Chunk code: 10 blocks × 1000 chars (150 overlap)
3. Deduplicate: 10 → 2 unique chunks (fingerprint matching)
4. Rank by instruction relevance
5. Select top 3 chunks
6. Assemble: instruction-first format
```

**Output:** 3,167 chars (62% reduction)  
**Result:** VPS generates actual async/await refactored code

## Network Architecture

**CM4 ↔ VPS Connection:**
- Protocol: HTTP/1.1 with SSE (Server-Sent Events)
- Transport: Tailscale VPN (encrypted WireGuard)
- CM4 endpoint: `http://127.0.0.1:9000` (via Tailscale tunnel)
- Connection: Persistent pool (httpx client)

**Client ↔ CM4:**
- Endpoint: `http://<cm4-ip>:7000`
- Authentication: Optional (can add API key)
- Streaming: SSE for real-time token delivery

**VPS Security:**
- Bind: `127.0.0.1:9000` (localhost only)
- Access: Tailscale tunnel or SSH tunnel only
- Auth: API key required for all inference endpoints
- Public: Health check only (`/health`)

## Performance Characteristics

### CM4 Overhead
- Request routing: <10ms
- Chunking (8KB prompt): <100ms
- Total orchestration: <100ms typical

### VPS Inference
- Small prompt (<100 chars): ~17s, 33 tokens (1.9 tok/s)
- Large prompt (8KB, chunked): ~182s, 129 tokens (0.7 tok/s)
- Model loading: 2-5s (first request only)

### Resource Usage
- CM4: ~500MB RAM (orchestrator + Python runtime)
- VPS: ~4GB RAM (model loaded, 7B quantized)

## Fault Tolerance

**Circuit Breaker Pattern:**
- VPS failure → Circuit opens
- 10s cooldown period
- Automatic recovery on success
- Prevents cascade failures

**Load Shedding:**
- Max 2 concurrent requests
- HTTP 503 when exceeded
- Protects CM4 from overload

**Request Correlation:**
- UUID tracking through full pipeline
- Enables end-to-end debugging
- Logged at each stage

## Technology Stack

### CM4 Dependencies
```python
fastapi==0.115.6
uvicorn==0.34.0
httpx==0.28.1
python-dotenv==1.0.1
pydantic==2.10.5
```

### VPS Dependencies
```python
fastapi==0.115.6
uvicorn==0.34.0
llama-cpp-python==0.3.4
python-dotenv==1.0.1
```

## Security Model

**Authentication:**
- VPS requires `X-API-Key` header
- Keys generated via `generate_api_key.sh`
- Keys stored in `.env` files (gitignored)

**Network Isolation:**
- VPS never exposed to public internet
- All access via Tailscale encrypted tunnel
- CM4 acts as sole authorized client

**Rate Limiting:**
- Load shedding (concurrent limit)
- VPS resource protection (CPU/RAM checks)
- No per-user quotas (single trusted client)

## Future Enhancements

**Planned Components:**
- `orchestration/` — multi-step task coordination
- `retrieval/` — optional retrieval augmentation (hardware-dependent)
- `analysis/` — static prompt/code analysis helpers
- `utils/` — shared helpers and primitives

**Potential Optimizations:**
- Multi-model support (DeepSeek Coder)
- Model swapping on demand
- AST-based chunking for Python
- Response caching layer
## File Structure
```
