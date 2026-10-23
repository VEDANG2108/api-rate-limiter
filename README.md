# Distributed API Rate Limiter & Token Bucket Middleware

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat&logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A high-performance ASGI rate-limiting middleware for FastAPI microservices implementing the Token Bucket algorithm with lazy state recomputation and concurrency guarantees.

---

## Architectural Design

```text
Incoming HTTP Request
       │
       ▼
[ RateLimitMiddleware ] (Extracts client ID: X-API-Key or IP)
       │
       ├── Path in Whitelist (/docs, /openapi.json)? ──► Bypass Limiter
       │
       ▼
[ TokenBucketLimiter Engine ] (asyncio.Lock safe)
       │
       ├── Compute Elapsed Time: Δt = t_now - t_last
       ├── Refill: tokens = min(capacity, previous_tokens + Δt * refill_rate)
       │
       ├── Tokens >= 1.0?
       │     ├── YES: Deduct 1.0 token
       │     │        Proceed to Route Handler
       │     │        Inject 'X-RateLimit-Limit' & 'X-RateLimit-Remaining'
       │     │
       │     └── NO:  Short-Circuit with HTTP 429 Too Many Requests
       │              Calculate Retry-After: (1.0 - tokens) / refill_rate
       │              Inject 'Retry-After' & Diagnostic Headers
```

---

## Key Features

- **Continuous Lazy Refill:** Evaluates token generation on-demand via monotonic delta calculations ($\Delta t \times R$), avoiding wasteful background pollers or timers.
- **Concurrency & Thread Safety:** Uses `asyncio.Lock` to guarantee atomic read-modify-write transitions across asynchronous event loop tasks.
- **RFC-Compliant Diagnostics:** Returns standard rate limit headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After`) with sub-second accuracy.
- **Identity Isolation:** Prioritizes authenticated tier limits (`X-API-Key`) with fallback to client network address (`request.client.host`).
- **Comprehensive Test Suite:** Unit and integration coverage testing burst limits, continuous refilling, isolation, and route exemptions using `pytest-asyncio`.

---

## Tech Stack

- **Framework:** FastAPI / Starlette (ASGI Middleware)
- **Language:** Python 3.13
- **Clock Engine:** `time.monotonic()` (Leap-second & clock drift resistant)
- **Testing:** Pytest, Pytest-Asyncio, HTTPX

---

## API Reference

### 1. Protected Resource
* **Endpoint:** `GET /api/v1/resource`
* **Headers:** `X-API-Key: <optional-key>`
* **Status:** `200 OK` (if tokens available) or `429 Too Many Requests` (if exhausted)

### 2. Reset Limiter
* **Endpoint:** `POST /api/v1/reset`
* **Status:** `200 OK` (Clears in-memory state for diagnostic evaluation)

---

## Setup & Running Locally

```bash
git clone [https://github.com/](https://github.com/)<your-username>/api-rate-limiter.git
cd api-rate-limiter
python -m venv venv

# Windows
.\venv\Scripts\Activate.ps1
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Run test suite:
```bash
python -m pytest -v
```