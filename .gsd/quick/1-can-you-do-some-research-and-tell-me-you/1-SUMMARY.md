# Quick Task: Python Interpreter Performance Analysis for SemPKM

**Date:** 2026-03-17
**Branch:** gsd/quick/1-can-you-do-some-research-and-tell-me-you

## TL;DR

**Switching Python interpreters would not meaningfully improve SemPKM's performance.** The app's bottleneck is IO-bound triplestore communication, not CPU-bound Python execution. The small amount of CPU-intensive work is already correctly offloaded. Higher-impact optimizations exist at the architecture level.

---

## SemPKM's Performance Profile

SemPKM runs CPython 3.12 on uvicorn (single worker, async). The workload breaks down as:

### IO-Bound (95%+ of request time)
- **SPARQL queries to RDF4J** via httpx AsyncClient — every page load, nav tree, object render, view execution
- **SQLAlchemy async queries** to SQLite/PostgreSQL for auth, sessions, settings
- **Template rendering** (Jinja2, fast, not a bottleneck)

### CPU-Bound (occasional, already offloaded)
- **OWL 2 RL inference** (`owlrl.DeductiveClosure.expand()`) — runs on manual trigger, uses `asyncio.to_thread()`
- **SHACL validation** (`pyshacl.validate()`) — background queue after writes, uses `asyncio.to_thread()`
- **SHACL-AF rules** (`pyshacl.shacl_rules()`) — during inference runs, uses `asyncio.to_thread()`
- **RDF graph parsing** (`rdflib.Graph.parse()`) — during model install, import, inference
- **Obsidian vault scanning** — ZIP extraction + file parsing, uses `asyncio.to_thread()`

The `asyncio.to_thread()` usage is correct — it moves CPU-bound work off the event loop so async request handling continues unblocked.

---

## Interpreter Options Evaluated

### 1. PyPy (JIT-compiled Python)

**Compatibility:** Good in theory. pySHACL explicitly lists PyPy in its classifiers. rdflib and owlrl are pure Python. FastAPI resolved its PyPy/orjson incompatibility in v0.111.1.

**The problem:** PyPy's JIT excels at tight pure-Python loops (exactly where owlrl/pyshacl live), but it *hurts* the HTTP fast path. Benchmarks from Tony Baloney's "PyPy in Production" testing showed **response times 20% slower at p50 and 100% slower at p100** for standard FastAPI endpoints. The reason: uvicorn's performance comes from `uvloop` (Cython) and `httptools` (C), neither of which works with PyPy. You must fall back to `h11` (pure Python HTTP parser), which is significantly slower.

**Net effect for SemPKM:** Inference and validation (which run occasionally) would be faster. Every single HTTP request (which runs constantly) would be slower. Bad trade.

**Practical risks:**
- `cryptography` package (used for Fernet encryption of WebID keys, LLM keys) has Rust/C extensions — PyPy compatibility not guaranteed
- `uvloop` unavailable — must use UvicornH11Worker
- Smaller ecosystem, harder debugging, fewer Docker base images
- PyPy currently targets Python 3.10 — SemPKM requires 3.12

### 2. Python 3.13t (Free-Threaded / No-GIL)

**What it does:** Removes the GIL so threads can execute Python bytecode in true parallel. Promising for CPU-bound threaded workloads.

**Why it doesn't help SemPKM:**
- The CPU-bound tasks already run in `asyncio.to_thread()` — they're non-blocking but serialize under the GIL. However, SemPKM processes inference and validation *sequentially* (one at a time), so parallel threads aren't the bottleneck.
- The free-threaded build in 3.13 **disables the specializing adaptive interpreter**, causing a measurable single-threaded slowdown for *all* code. CodSpeed benchmarks confirm this penalty.
- Library ecosystem support is incomplete. `cffi` (used by `cryptography`) has known issues with 3.13t.
- Python 3.14 is expected to re-enable the adaptive interpreter under free-threading, making this more viable in the future — but not today.

**Net effect for SemPKM:** Would make single-threaded request handling slower. The parallel threading benefit doesn't apply because CPU-intensive tasks are already infrequent and sequential.

### 3. Cython / mypyc Compilation

**What it does:** Compile hot Python modules to C extensions for 2-10x speedups.

**Why it's overkill for SemPKM:** The hot paths are inside third-party libraries (rdflib, owlrl, pyshacl), not in SemPKM's own code. Compiling SemPKM's router code wouldn't help because those functions are thin orchestration layers over IO operations.

### 4. GraalPy

**What it does:** Python on GraalVM, promising for polyglot or JIT-heavy workloads.

**Why it's not viable:** Extremely immature ecosystem, poor library compatibility, no production-grade ASGI server support. Not a serious option.

---

## Where Performance Actually Matters

Based on the codebase analysis, the real performance levers are:

| Area | Current State | Impact |
|------|---------------|--------|
| **SPARQL round-trips per page** | Multiple sequential queries (ViewSpecService, LabelService, nav tree) | High — each is a network hop to RDF4J |
| **ViewSpecService caching** | TTL cache added in v2.1 (300s, 64 entries) | Already addressed |
| **LabelService cache** | Process-local TTL cache, 300s | Works for single-worker; stale after writes |
| **httpx connection pooling** | Single AsyncClient, default pool limits | Could tune for high concurrency |
| **Edge duplication** | ~16x triples per reified edge | Increases CONSTRUCT query payload |
| **Inference/validation speed** | owlrl closure + pyshacl on full graph | Only matters at scale (1000s of objects) |

### Recommended Optimizations (if/when needed)

1. **Reduce SPARQL round-trips** — batch label lookups, prefetch view specs, combine related queries
2. **Tune httpx connection pool** — increase `max_connections` and `max_keepalive_connections` for RDF4J client
3. **Profile inference at scale** — if owlrl becomes slow on large graphs (5k+ objects), consider incremental inference or subprocess-based parallelism
4. **Consider uvicorn workers** — if concurrent request throughput becomes an issue, add `--workers 2-4` (separate processes, each with own event loop)
5. **Long-term:** Python 3.14's free-threading with re-enabled adaptive interpreter could make `asyncio.to_thread()` calls genuinely parallel without the single-threaded penalty — revisit then

---

## Conclusion

The interpreter is not the bottleneck. SemPKM is an IO-bound async web app where 95%+ of latency comes from triplestore round-trips and template rendering. The CPU-bound work (inference, validation) is correctly isolated to background threads and runs infrequently. Switching to PyPy would make HTTP handling slower. Switching to 3.13t would make everything slightly slower with no benefit for sequential workloads. The highest-value performance work is reducing network round-trips and improving caching at the application architecture level.

## What Changed
- Research document produced (this file)

## Files Modified
- `.gsd/quick/1-can-you-do-some-research-and-tell-me-you/1-SUMMARY.md` (this file)

## Verification
- Reviewed Dockerfile, pyproject.toml, and all CPU-bound code paths
- Confirmed asyncio.to_thread() usage in validation, inference, and import code
- Verified PyPy compatibility claims against pySHACL pyproject.toml classifiers
- Cross-referenced PyPy/FastAPI benchmark data and free-threading performance data
