# Cerebrum Performance & Optimization

Performance characteristics, design decisions, and optimization strategies for the Cerebrum distributed AI system.

## Table of Contents

- [Performance Overview](#performance-overview)
- [Workload Separation](#workload-separation)
- [Measured Performance](#measured-performance)
- [Resource Constraints](#resource-constraints)
- [Optimization Strategies](#optimization-strategies)
- [Future Improvements](#future-improvements)

---

## Performance Overview

Cerebrum achieves production-grade AI code generation on modest hardware through intelligent workload distribution and careful resource management.

**Key Metrics:**
- **CM4 Overhead:** <100ms (routing, chunking, coordination)
- **VPS Inference:** 1.6 tok/s average (CPU-only, single-threaded)
- **Context Reduction:** Up to 82% via smart chunking
- **Memory Footprint:** ~500MB (CM4), ~4GB (VPS with model loaded)

---

## Workload Separation

### CM4 Orchestrator (Raspberry Pi)

**Handles millisecond-scale operations:**

| Task | Typical Time | Bottleneck |
|------|-------------|------------|
| Request parsing | <1ms | None |
| Instruction extraction | 1-5ms | String operations |
| Chunking (8KB prompt) | 50-100ms | CPU (string ops) |
| Deduplication | 10-20ms | Hashing |
| Model selection | <1ms | Lookup |
| SSE proxying | <10ms/token | Network I/O |

**Strengths:**
- Fast I/O (network, disk)
- Low latency for coordination
- Efficient at string operations
- Low idle power consumption

**Excluded Responsibilities:**
- Model inference (CPU/RAM intensive)
- Heavy numerical computation
- Long-running CPU tasks

### VPS Backend

**Handles second-scale operations:**

| Task | Typical Time | Bottleneck |
|------|-------------|------------|
| Model loading | 2-5s | Disk I/O, memory allocation |
| Token generation | 0.5-2.0s/token | CPU (matrix ops) |
| Streaming response | <10ms/token | Network I/O |

**Why VPS excels:**
- Sustained CPU performance
- Sufficient RAM for 7B models
- Always-on availability
- Expandable resources

**Deliberately single-threaded:**
- One model loaded at a time
- Predictable memory usage
- Simpler resource management
- Easier debugging

---

## Measured Performance

### Real-World Benchmarks

**Test Environment:**
- CM4: Raspberry Pi CM4, 4GB RAM, Debian Bookworm
- VPS: 4GB RAM, 2 vCPU, Debian 12
- Model: Qwen-7B Q4 quantized
- Network: Tailscale VPN

#### Test 1: Small Prompt (No Chunking)
````bash
Input:  "def hello():"
Length: 12 chars
Tokens: 33 generated
Time:   17.11s
Rate:   1.93 tok/s
````

**Breakdown:**
````
CM4 routing:        <10ms
VPS model loading:  2.1s (first request)
VPS inference:      15.0s
CM4 streaming:      <100ms
Total:             17.11s
````

**Observation:** Most time is inference. CM4 overhead negligible.

#### Test 2: Large Prompt (With Chunking)
````bash
Input:  Repeated synchronous code (5x) + refactoring instruction
Length: 8,344 chars
Chunks: 10 blocks → 2 unique (dedup) → top 3 selected
Output: 3,167 chars (62% reduction)
Tokens: 129 generated
Time:   182.14s
Rate:   0.71 tok/s
````

**Breakdown:**
````
CM4 instruction extraction:  5ms
CM4 chunking:               50ms
CM4 deduplication:          20ms
CM4 ranking:                15ms
CM4 prompt assembly:        10ms
VPS inference:             182.0s
Total CM4 overhead:        100ms (<0.1% of total)
````

**Key insight:** Chunking overhead is trivial compared to inference time. The 62% context reduction more than pays for itself.

**Result quality:** Generated actual async/await refactored code (not TODO lists or meta-commentary).

#### Test 3: Concurrent Requests (Load Shedding)
````bash
Request 1: Started, processing
Request 2: Started, processing
Request 3: 503 Service Unavailable (load shed)

Max concurrent: 2
Exceeded:      Returns 503 immediately
Recovery:      Automatic when slot available
````

**Why limit to 2:**
- CM4 has limited RAM (~3.7GB available)
- Each request holds prompt in memory
- SSE streaming connections persist
- Prevents thrashing/OOM

### Context Optimization Impact

**Without chunking:**
````
Prompt: 8,344 chars
VPS processing: Full context
Estimated time: ~200s
Risk: Context overflow, poor quality
````

**With smart chunking:**
````
Prompt: 3,167 chars (62% smaller)
VPS processing: Relevant chunks only
Actual time: 182s
Quality: High (instruction preserved, focused context)
````

**Savings:** 18s + improved output quality

---

## Resource Constraints

### CM4 Limits

**Hardware:**
````
CPU:  BCM2711 (4 cores @ 1.5 GHz)
RAM:  4GB total, ~3.7GB available
Storage: microSD (write-limited)
Network: 1 Gbps Ethernet
````

**Observed bottlenecks:**
1. **RAM** (most critical)
   - System: ~300MB
   - Orchestrator: ~500MB
   - Headroom: ~2.9GB for requests
   - Chunking helps manage large prompts

2. **CPU** (rarely saturated)
   - Chunking: <100ms even for 8KB
   - String ops highly efficient
   - Network I/O dominant

3. **Storage** (write endurance)
   - Logs rotate to prevent SD wear
   - No model storage (all on VPS)
   - FAISS deferred until NVMe

**Protection mechanisms:**
- Load shedding (max 2 concurrent)
- Request size limits (16KB)
- No caching to disk (memory only)

### VPS Limits

**Hardware:**
````
CPU:  2 vCPU
RAM:  7.26GB total
Storage: 160GB NVMe
Network: 1 Gbps
````

**Observed bottlenecks:**
1. **CPU** (always at limit during inference)
   - Single-threaded llama.cpp
   - 100% usage normal during generation
   - Rate: ~1.6 tok/s average

2. **RAM** (carefully managed)
   - Model: ~4GB (7B Q4)
   - System: ~2GB
   - Headroom: ~1.2GB
   - Auto-unload after 60min idle

3. **Storage** (not a bottleneck)
   - Models: ~8GB total
   - Logs: Minimal
   - NVMe handles writes easily

**Protection mechanisms:**
- CPU limit: Reject when >70%
- RAM limit: Reject when <1GB free
- Model auto-unload (idle timeout)
- Single model at a time

---

## Optimization Strategies

### 1. Smart Chunking (Implemented)

**Problem:** Large prompts (8KB+) slow inference and may lose important context.

**Solution:** Intelligent chunk selection
````python
1. Extract instruction (task definition)
2. Chunk code into 1000-char blocks (150 overlap)
3. Deduplicate repeated patterns
4. Rank chunks by relevance to instruction
5. Select top 3 chunks
6. Assemble: instruction-first format
````

**Results:**
- 62-82% size reduction typical
- <100ms overhead
- Preserves task intent
- Improves output quality

**When NOT to chunk:**
- Prompt <1,500 chars (overhead not worth it)
- Reduction <10% (assembly overhead > savings)
- No instruction detected (ranking unreliable)

### 2. Instruction-First Assembly (Implemented)

**Problem:** Base code models trained on incomplete prompts, need behavioral cues.

**Solution:** Place instruction before code
````markdown
# INSTRUCTION: Refactor to use async/await

Here is the code:
```python
[code chunks]
```

Refactored code:
```python
```

**Results:**
- Model focuses on task, not completion
- Reduces meta-commentary
- Generates actual refactored code

### 3. Deduplication (Implemented)

**Problem:** Repeated code blocks create redundant chunks.

**Solution:** Hash-based fingerprinting
```python
def dedupe_chunks(chunks: List[str]) -> List[str]:
    seen = set()
    unique = []
    for chunk in chunks:
        fingerprint = hash(chunk.strip()[:100])
        if fingerprint not in seen:
            seen.add(fingerprint)
            unique.append(chunk)
    return unique
```

**Results:**
- 10 chunks → 2 unique (80% reduction in test case)
- Handles overlap variations
- Minimal CPU overhead

### 4. Circuit Breaker Pattern (Implemented)

**Problem:** VPS failures cascade to all requests.

**Solution:** Fail-fast with automatic recovery
```python
- VPS fails → Circuit opens
- Reject new requests for 10s
- Test request after cooldown
- Success → Circuit closes
- Failure → Extend cooldown
```

**Results:**
- Prevents thundering herd
- CM4 stays responsive
- Automatic recovery
- Clear error messages

### 5. Connection Pooling (Implemented)

**Problem:** Creating new HTTP connections for each request adds latency.

**Solution:** Persistent httpx client
```python
client = httpx.AsyncClient(
    timeout=300.0,
    limits=httpx.Limits(
        max_keepalive_connections=5,
        max_connections=10
    )
)
```

**Results:**
- Reuses TCP connections
- Lower latency per request
- Fewer resources consumed

### 6. Load Shedding (Implemented)

**Problem:** Too many concurrent requests exhaust RAM.

**Solution:** Explicit concurrency limit
```python
MAX_CONCURRENT = 2

if active_requests >= MAX_CONCURRENT:
    return 503  # Service Unavailable
```

**Results:**
- Prevents OOM on CM4
- Clear failure mode (503)
- Self-healing (auto-recovery)

### 7. Streaming SSE (Implemented)

**Problem:** Waiting for full response adds perceived latency.

**Solution:** Token-by-token streaming
```python
for token in model.generate_stream():
    yield f"data: {json.dumps({'token': token})}\n\n"
```

**Results:**
- User sees progress immediately
- Perceived latency reduced
- Can stop generation early

---

## Performance Anti-Patterns (Avoided)

### Running Models on CM4

**Why not:**
- 7B model needs ~4GB RAM (would OOM)
- CPU too slow (~0.1 tok/s estimated)
- No headroom for system/orchestration

**Better:** Delegate to VPS

### Multiple Concurrent VPS Models

**Why not:**
- 2 models = 8GB RAM (exceeds VPS capacity)
- Context switching overhead
- Unpredictable memory usage

**Better:** Single model, queue requests

### Aggressive Caching

**Why not:**
- Code generation rarely repeats exactly
- Cache invalidation complex
- Wastes CM4 RAM

**Better:** Stateless, compute on-demand

### Synchronous VPS Calls

**Why not:**
- Blocks CM4 event loop
- Can't handle concurrent requests
- Worse user experience

**Better:** Async/await throughout

---

## Future Improvements

### Near-Term (Achievable with Current Hardware)

**1. AST-Based Chunking (Python)**
```python
# Current: Dumb 1000-char blocks
# Future: Chunk by function/class boundaries
import ast
tree = ast.parse(code)
chunks = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
```

**Benefit:** More semantically meaningful chunks  
**Effort:** Medium (2-3 days)

**2. Response Caching (Selective)**
```python
# Cache only deterministic queries
if temperature == 0.0 and prompt in cache:
    return cache[prompt]
```

**Benefit:** Instant responses for repeated queries  
**Effort:** Low (1 day)  
**Caveat:** Limited hit rate for code generation

**3. Batch Requests (API)**
```python
POST /v1/complete/batch
{
  "requests": [
    {"prompt": "def a():", "language": "python"},
    {"prompt": "fn b() {", "language": "rust"}
  ]
}
```

**Benefit:** Better throughput for bulk jobs  
**Effort:** Medium (API changes + testing)

### Long-Term (Requires Hardware Upgrades)

**1. FAISS Semantic Search**
- **Blocker:** microSD write endurance
- **Requires:** NVMe SSD (+ CM5 upgrade)
- **Benefit:** RAG, example-based completion

**2. Multi-Model Support**
- **Blocker:** VPS RAM (7GB total)
- **Requires:** 16GB VPS or model swapping
- **Benefit:** Specialized models per language

**3. GPU Acceleration**
- **Blocker:** No GPU on VPS
- **Requires:** GPU-enabled VPS or local GPU
- **Benefit:** 10-50x faster inference

**4. Quantization Optimization**
- **Current:** Q4 (4-bit)
- **Future:** Q3 or Q2 for smaller models
- **Benefit:** Lower RAM, faster loading
- **Risk:** Quality degradation

---

## Benchmarking Tools

### CM4 Overhead Measurement
```bash
# Time chunking operation
ssh <cm4-user>@<cm4-host>
cd /opt/cerebrum-pi
python3 << EOF
import time
from cerebrum.retrieval.chunker import chunk_text

text = "x" * 8000
start = time.time()
chunks = chunk_text(text, max_chars=1000, overlap=150)
end = time.time()
print(f"Chunking 8KB: {(end-start)*1000:.2f}ms")
EOF
```

### VPS Inference Speed
```bash
# Measure tok/s
ssh <vps-user>@<vps-host>

curl -X POST http://127.0.0.1:9000/v1/inference \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $(grep CEREBRUM_API_KEY .env | cut -d= -f2)" \
  -d '{"prompt": "def test():", "model": "qwen_7b", "max_tokens": 100}' \
  | jq '.inference_time, .total_tokens' \
  | awk 'NR==1 {time=$1} NR==2 {tokens=$1; print tokens/time " tok/s"}'
```

### End-to-End Latency
```bash
# Full request through CM4 → VPS → CM4
time curl -X POST http://localhost:7000/v1/complete \
  -H "Content-Type: application/json" \
  -d '{"prompt": "def hello():", "language": "python", "max_tokens": 50}'
```

---

## Performance Tuning Guide

### If Inference is Slow

**Diagnosis:**
```bash
# Check VPS CPU
ssh <vps-user>@<vps-host>
htop  # Should see uvicorn at ~100% during inference
```

**Solutions:**
1. Reduce `max_tokens` (fewer tokens = faster)
2. Use smaller model (7B → smaller, but quality drops)
3. Upgrade VPS CPU (more cores doesn't help—single-threaded)
4. Consider GPU VPS (10-50x speedup)

### If CM4 Runs Out of Memory

**Diagnosis:**
```bash
ssh <cm4-user>@<cm4-host>
free -h  # Check available RAM
```

**Solutions:**
1. Reduce `MAX_CONCURRENT` (default: 2)
2. Implement stricter prompt size limits
3. Increase chunking aggressiveness
4. Upgrade to 8GB CM4 (when available)

### If Chunking Overhead is High

**Diagnosis:**
```bash
# Check logs for chunking time
grep "Chunking complete" logs/cerebrum.log
```

**Solutions:**
1. Increase `CHUNKING_THRESHOLD` (currently 1500)
2. Reduce `CHUNK_SIZE` (less to process)
3. Skip deduplication for small prompts

### If VPS Rejects Requests

**Diagnosis:**
```bash
# Check VPS health
curl http://127.0.0.1:9000/health | jq '.cpu_percent, .memory_available_mb'
```

**Solutions:**
1. Unload idle models: `curl -X POST .../v1/cleanup`
2. Restart VPS: `sudo systemctl restart cerebrum-backend`
3. Increase RAM limits in `.env`
4. Upgrade VPS resources

---

## Profiling & Monitoring

### Continuous Monitoring

**CM4 Dashboard:**
```bash
watch -n 2 'curl -s http://localhost:7000/v1/stats | jq'
```

**VPS Dashboard:**
```bash
watch -n 2 'curl -s -H "X-API-Key: KEY" http://127.0.0.1:9000/v1/stats | jq'
```

### Log Analysis

**Find slow requests:**
```bash
grep "POST /v1/complete" logs/cerebrum.log | awk '{print $(NF-1)}' | sort -n | tail -10
```

**Average response time:**
```bash
grep "POST /v1/complete" logs/cerebrum.log | awk '{sum+=$(NF-1); count++} END {print sum/count "s"}'
```

**Chunking effectiveness:**
```bash
grep "Chunking complete" logs/cerebrum.log | awk -F'→' '{print $2}' | awk '{print $1}'
```

---

## Lessons Learned

1. **Distribution beats raw power:** CM4 + VPS outperforms local-only solutions
2. **Chunking is worth it:** <100ms overhead, 60%+ context reduction
3. **Streaming is essential:** Perceived latency matters more than total time
4. **Resource limits are features:** Load shedding prevents cascading failures
5. **Single-threaded is fine:** Simpler > faster (for this use case)
6. **Context quality > quantity:** Smart selection beats naive inclusion
7. **Measure everything:** Assumptions fail, data doesn't

---

## Performance Checklist

Before deploying optimizations:

- [ ] Benchmark current performance (baseline)
- [ ] Test on actual hardware (not just macOS)
- [ ] Measure CM4 overhead separately
- [ ] Measure VPS inference separately
- [ ] Check memory usage under load
- [ ] Verify error handling (OOM, timeout, etc.)
- [ ] Test edge cases (huge prompts, concurrent requests)
- [ ] Monitor for regressions
- [ ] Document changes and rationale
- [ ] Update this document

---

## Resources

- **Chunking Implementation:** [`cerebrum/retrieval/chunker.py`](../../cerebrum-pi/cerebrum/retrieval/chunker.py)
- **Circuit Breaker:** [`cerebrum/core/vps_client.py`](../../cerebrum-pi/cerebrum/core/vps_client.py)
- **Load Shedding:** [`cerebrum/api/middleware/load_shed.py`](../../cerebrum-pi/cerebrum/api/middleware/load_shed.py)
- **VPS Inference:** [`vps_server/main.py`](../../cerebrum-backend/vps_server/main.py)
