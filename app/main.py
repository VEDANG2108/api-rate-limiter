from fastapi import FastAPI, Header
from typing import Optional
from app.limiter import TokenBucketLimiter
from app.middleware import RateLimitMiddleware

# Configure capacity=5 tokens, refill_rate=1 token/second for easy manual testing
limiter = TokenBucketLimiter(capacity=5.0, refill_rate=1.0)

app = FastAPI(
    title="Distributed API Rate Limiter",
    description="High-throughput API gateway middleware using the Token Bucket algorithm."
)

# Attach the custom rate limiting middleware
app.add_middleware(RateLimitMiddleware, limiter=limiter)

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "Token Bucket Rate Limiter Gateway",
        "documentation": "/docs"
    }

@app.get("/api/v1/resource")
def get_resource(x_api_key: Optional[str] = Header(default=None)):
    """
    Standard protected resource endpoint.
    Throttled per client IP or 'X-API-Key' header if provided.
    """
    return {
        "data": "Operation successful.",
        "payload": [1, 2, 3, 4, 5]
    }

@app.post("/api/v1/reset")
async def reset_limits():
    """Diagnostic route to clear in-memory rate limit records."""
    await limiter.reset()
    return {"status": "buckets cleared"}