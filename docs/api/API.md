# Cerebrum API Reference

Complete API documentation for the Cerebrum distributed AI code generation system.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [CM4 Orchestrator API](#cm4-orchestrator-api-port-7000)
- [VPS Backend API](#vps-backend-api-port-9000)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)

---

## Overview

Cerebrum exposes two APIs:

| Component | Port | Purpose | Public |
|-----------|------|---------|--------|
| **CM4 Orchestrator** | 7000 | User-facing completion & management | Yes (local network) |
| **VPS Backend** | 9000 | Internal inference engine | No (Tailscale only) |

**Typical flow:**
1. Client → CM4:7000 (code completion request)
2. CM4 → VPS:9000 (prepared prompt)
3. VPS → CM4 (streamed tokens)
4. CM4 → Client (proxied stream)

---

## Authentication

### CM4 Orchestrator (Port 7000)

**Currently:** No authentication required (designed for single-user local access)

**Future:** Optional API key via header:
```http
X-API-Key: your-key-here
```

### VPS Backend (Port 9000)

**Required for all endpoints except `/health`:**
```http
X-API-Key: your-cerebrum-api-key
```

**Generating keys:**
```bash
cd ~/Cerebrum/cerebrum-backend/scripts
./generate_api_key.sh
```

Keys are stored in `.env` files and must match between CM4 and VPS.

---

## CM4 Orchestrator API (Port 7000)

Base URL: `http://<cm4-ip>:7000`

### Endpoints

#### `GET /health`

Health check endpoint.

**Request:**
```bash
curl http://localhost:7000/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-25T12:00:00.000000",
  "vps_available": true,
  "uptime": 3600.5
}
```

**Status Codes:**
- `200 OK` - Service healthy
- `503 Service Unavailable` - VPS backend unreachable

---

#### `POST /v1/complete`

Non-streaming code completion.

**Request:**
```bash
curl -X POST http://localhost:7000/v1/complete \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "def fibonacci(n):",
    "language": "python",
    "max_tokens": 256,
    "temperature": 0.4
  }'
```

**Request Body:**
```json
{
  "prompt": "string (required)",
  "language": "string (required)",
  "max_tokens": "integer (optional, default: 512)",
  "temperature": "float (optional, default: 0.4, range: 0.0-1.0)"
}
```

**Supported Languages:**
- `python`, `javascript`, `typescript` → Uses Qwen-7B
- `rust`, `c`, `cpp`, `go` → Uses CodeLLaMA-7B

**Response:**
```json
{
  "completion": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
  "language": "python",
  "model": "qwen_7b",
  "total_tokens": 42,
  "inference_time": 18.234,
  "timestamp": "2025-12-25T12:00:00.000000"
}
```

**Status Codes:**
- `200 OK` - Success
- `400 Bad Request` - Invalid parameters
- `503 Service Unavailable` - VPS unreachable or overloaded
- `429 Too Many Requests` - Load shedding active (>2 concurrent)

---

#### `POST /v1/complete/stream`

Streaming code completion (Server-Sent Events).

**Request:**
```bash
curl -N -X POST http://localhost:7000/v1/complete/stream \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "async def fetch():",
    "language": "python",
    "max_tokens": 128,
    "temperature": 0.4
  }'
```

**Request Body:** Same as `/v1/complete`

**Response:** Server-Sent Events (SSE)
```
data: {"token": "import", "total_tokens": 1}

data: {"token": " aiohttp", "total_tokens": 2}

data: {"token": "\n", "total_tokens": 3}

data: {"token": "async", "total_tokens": 4}

data: {"token": " def", "total_tokens": 5}

...

data: {"done": true, "language": "python", "model": "qwen_7b", "total_tokens": 128, "inference_time": 182.14, "timestamp": "2025-12-25T12:00:00.000000"}
```

**Event Types:**

**Token event:**
```json
{
  "token": "string",
  "total_tokens": "integer"
}
```

**Done event:**
```json
{
  "done": true,
  "language": "string",
  "model": "string",
  "total_tokens": "integer",
  "inference_time": "float (seconds)",
  "timestamp": "string (ISO 8601)"
}
```

**Error event:**
```json
{
  "error": true,
  "message": "string",
  "code": "string"
}
```

**Client Implementation:**
```javascript
const response = await fetch('http://localhost:7000/v1/complete/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    prompt: 'def hello():',
    language: 'python',
    max_tokens: 128
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      if (data.token) {
        process.stdout.write(data.token);
      } else if (data.done) {
        console.log(`\n[${data.total_tokens} tokens in ${data.inference_time}s]`);
      }
    }
  }
}
```

---

#### `GET /v1/models`

List available models.

**Request:**
```bash
curl http://localhost:7000/v1/models
```

**Response:**
```json
{
  "models": [
    {
      "id": "qwen_7b",
      "name": "Qwen 7B",
      "languages": ["python", "javascript", "typescript"],
      "parameters": "7B",
      "quantization": "Q4"
    },
    {
      "id": "codellama_7b",
      "name": "CodeLLaMA 7B",
      "languages": ["rust", "c", "cpp", "go"],
      "parameters": "7B",
      "quantization": "Q4"
    }
  ]
}
```

---

#### `GET /v1/stats`

System statistics.

**Request:**
```bash
curl http://localhost:7000/v1/stats
```

**Response:**
```json
{
  "uptime": 3600.5,
  "requests_total": 142,
  "requests_active": 1,
  "vps_available": true,
  "vps_response_time_ms": 12.3,
  "memory_mb": 487.2,
  "load_avg": [0.5, 0.6, 0.7]
}
```

---

## VPS Backend API (Port 9000)

Base URL: `http://127.0.0.1:9000` (localhost only, via Tailscale)

**⚠️ Internal API:** Not intended for direct client access. Used by CM4 Orchestrator only.

### Endpoints

#### `GET /health`

Health check (no authentication required).

**Request:**
```bash
curl http://127.0.0.1:9000/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-25T12:00:00.000000",
  "cpu_percent": 45.2,
  "memory_available_mb": 2048.5,
  "models_loaded": ["qwen_7b"]
}
```

---

#### `POST /v1/inference`

Internal inference endpoint (non-streaming).

**⚠️ Requires authentication**

**Request:**
```bash
curl -X POST http://127.0.0.1:9000/v1/inference \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key-here" \
  -d '{
    "prompt": "def hello():",
    "model": "qwen_7b",
    "max_tokens": 128,
    "temperature": 0.4
  }'
```

**Request Body:**
```json
{
  "prompt": "string (required)",
  "model": "string (required)",
  "max_tokens": "integer (optional, default: 512)",
  "temperature": "float (optional, default: 0.4)"
}
```

**Response:**
```json
{
  "completion": "def hello():\n    print(\"Hello, world!\")",
  "model": "qwen_7b",
  "total_tokens": 12,
  "inference_time": 8.234
}
```

---

#### `POST /v1/inference/stream`

Internal streaming inference endpoint.

**⚠️ Requires authentication**

**Request:** Same as `/v1/inference` but returns SSE stream

**Response:** Server-Sent Events (same format as CM4 streaming)

---

#### `GET /v1/models`

List loaded models.

**⚠️ Requires authentication**

**Request:**
```bash
curl -H "X-API-Key: your-key-here" \
  http://127.0.0.1:9000/v1/models
```

**Response:**
```json
{
  "models": [
    {
      "id": "qwen_7b",
      "loaded": true,
      "path": "/home/user/Cerebrum/cerebrum-backend/models/qwen-7b-q4.gguf",
      "memory_mb": 3840.2,
      "last_used": "2025-12-25T11:55:00.000000"
    },
    {
      "id": "codellama_7b",
      "loaded": false,
      "path": "/home/user/Cerebrum/cerebrum-backend/models/codellama-7b-q4.gguf"
    }
  ]
}
```

---

#### `GET /v1/stats`

System resource statistics.

**⚠️ Requires authentication**

**Request:**
```bash
curl -H "X-API-Key: your-key-here" \
  http://127.0.0.1:9000/v1/stats
```

**Response:**
```json
{
  "cpu_percent": 45.2,
  "memory_total_mb": 7260.0,
  "memory_available_mb": 2048.5,
  "memory_used_mb": 5211.5,
  "models_loaded": 1,
  "requests_total": 87,
  "requests_active": 0,
  "uptime": 7200.3
}
```

---

#### `POST /v1/unload/{model}`

Manually unload a model from memory.

**⚠️ Requires authentication**

**Request:**
```bash
curl -X POST \
  -H "X-API-Key: your-key-here" \
  http://127.0.0.1:9000/v1/unload/qwen_7b
```

**Response:**
```json
{
  "model": "qwen_7b",
  "unloaded": true,
  "memory_freed_mb": 3840.2
}
```

---

#### `POST /v1/cleanup`

Unload all idle models (not used in last 60 minutes).

**⚠️ Requires authentication**

**Request:**
```bash
curl -X POST \
  -H "X-API-Key: your-key-here" \
  http://127.0.0.1:9000/v1/cleanup
```

**Response:**
```json
{
  "models_unloaded": ["qwen_7b"],
  "memory_freed_mb": 3840.2
}
```

---

## Error Handling

### Error Response Format

All errors return JSON with this structure:
```json
{
  "error": true,
  "message": "Human-readable error description",
  "code": "ERROR_CODE",
  "timestamp": "2025-12-25T12:00:00.000000"
}
```

### Common Error Codes

| Code | HTTP Status | Meaning |
|------|-------------|---------|
| `INVALID_REQUEST` | 400 | Missing or invalid parameters |
| `UNAUTHORIZED` | 401 | Missing or invalid API key |
| `RATE_LIMIT` | 429 | Load shedding active |
| `VPS_UNAVAILABLE` | 503 | Backend unreachable |
| `MODEL_NOT_FOUND` | 404 | Requested model doesn't exist |
| `RESOURCE_EXHAUSTED` | 503 | CPU/RAM limits exceeded |

### Example Error Response
```json
{
  "error": true,
  "message": "VPS backend is unavailable (circuit breaker open)",
  "code": "VPS_UNAVAILABLE",
  "timestamp": "2025-12-25T12:00:00.000000"
}
```

---

## Rate Limiting

### CM4 Orchestrator

**Load Shedding:**
- **Max concurrent requests:** 2
- **Exceeded behavior:** Returns `429 Too Many Requests`
- **No retry-after header** (client should implement exponential backoff)

**Recommended client retry:**
```javascript
async function retryRequest(fn, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (err) {
      if (err.status === 429 && i < maxRetries - 1) {
        await new Promise(r => setTimeout(r, Math.pow(2, i) * 1000));
        continue;
      }
      throw err;
    }
  }
}
```

### VPS Backend

**Resource Protection:**
- Rejects when CPU > 70%
- Rejects when RAM < 1GB available
- Returns `503 Service Unavailable`

---

## Request IDs

Every request through the CM4 generates a correlation ID for debugging:

**Response Header:**
```http
X-Request-ID: 65652caa-c647-4685-be81-5e51bc97f453
```

**Logging:**
```
2025-12-25 12:00:00 - INFO - [65652caa-c647-4685-be81-5e51bc97f453] POST /v1/complete/stream 200 182.14s
```

Use this ID when reporting issues or debugging.

---

## Client Libraries

### Official
- **Bash:** `scripts/cerebrum_repl.sh` (streaming REPL)

### Community
None yet - PRs welcome!

### Example Implementations

**Python (streaming):**
```python
import httpx

async def stream_completion(prompt: str, language: str = "python"):
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "http://localhost:7000/v1/complete/stream",
            json={
                "prompt": prompt,
                "language": language,
                "max_tokens": 256
            },
            timeout=300.0
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if "token" in data:
                        print(data["token"], end="", flush=True)
                    elif data.get("done"):
                        print(f"\n[{data['total_tokens']} tokens]")
```

**JavaScript (fetch API):**
See streaming example in `/v1/complete/stream` section above.

---

## API Versioning

**Current Version:** `v1`

All endpoints are prefixed with `/v1/`. Breaking changes will increment the version (`/v2/`), with `/v1/` maintained for compatibility.

---

## Support

**Issues:** https://github.com/artcore-c/Cerebrum/issues  
**Discussions:** https://github.com/artcore-c/Cerebrum/discussions

For VPS backend issues, check:
```bash
ssh user@vps
sudo journalctl -u cerebrum-backend -f
```

For CM4 orchestrator issues:
```bash
tail -f /opt/cerebrum-pi/logs/cerebrum.log
```