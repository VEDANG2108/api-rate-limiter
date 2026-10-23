from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from app.limiter import TokenBucketLimiter

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    ASGI Middleware that enforces token-bucket rate limits per client IP or API key.
    Injects standard RFC-compliant rate limit response headers.
    """
    def __init__(self, app, limiter: TokenBucketLimiter):
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next) -> Response:
        # Exempt documentation and OpenAPI schema endpoints from throttling
        if request.url.path in ("/docs", "/redoc", "/openapi.json", "/favicon.ico"):
            return await call_next(request)

        # Identify client by 'X-API-Key' header if present; fall back to client IP address
        api_key = request.headers.get("X-API-Key")
        if api_key:
            client_id = f"key:{api_key}"
        elif request.client and request.client.host:
            client_id = f"ip:{request.client.host}"
        else:
            client_id = "ip:anonymous"

        # Check token availability in the bucket
        is_allowed, remaining_tokens, retry_after = await self.limiter.consume(client_id)

        # Case 1: Rate limit exceeded (Reject immediately)
        if not is_allowed:
            headers = {
                "X-RateLimit-Limit": str(int(self.limiter.capacity)),
                "X-RateLimit-Remaining": "0",
                "Retry-After": str(int(retry_after) if retry_after >= 1 else 1),
            }
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "message": f"Rate limit quota exceeded. Retry after {retry_after} seconds.",
                    "client_identifier": client_id,
                },
                headers=headers,
            )

        # Case 2: Request allowed (Proceed to route handler)
        response = await call_next(request)

        # Attach rate limit diagnostic headers to outgoing successful response
        response.headers["X-RateLimit-Limit"] = str(int(self.limiter.capacity))
        response.headers["X-RateLimit-Remaining"] = str(remaining_tokens)

        return response