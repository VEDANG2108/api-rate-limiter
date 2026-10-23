import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app, limiter
from app.limiter import TokenBucketLimiter

client = TestClient(app)

@pytest.fixture(autouse=True)
async def reset_limiter_state():
    """Ensure every test starts with fresh, full buckets."""
    await limiter.reset()

def test_burst_capacity_and_throttling():
    """Verify exactly 5 requests succeed, and the 6th is rejected with 429."""
    for i in range(5):
        res = client.get("/api/v1/resource")
        assert res.status_code == 200
        assert int(res.headers["X-RateLimit-Remaining"]) == (4 - i)

    # 6th request exhausts capacity
    failed_res = client.get("/api/v1/resource")
    assert failed_res.status_code == 429
    assert failed_res.json()["error"] == "Too Many Requests"
    assert "Retry-After" in failed_res.headers

def test_token_refill_over_time():
    """Verify that waiting allows tokens to refill continuously."""
    # Consume all 5 tokens
    for _ in range(5):
        assert client.get("/api/v1/resource").status_code == 200

    assert client.get("/api/v1/resource").status_code == 429

    # Wait 1.1 seconds for at least 1 token to refill (refill_rate = 1.0/sec)
    asyncio.run(asyncio.sleep(1.1))

    # Next request should succeed
    retry_res = client.get("/api/v1/resource")
    assert retry_res.status_code == 200

def test_api_key_isolation():
    """Verify that limits on one API key do not throttle a different client."""
    headers_user_a = {"X-API-Key": "user-alpha"}
    headers_user_b = {"X-API-Key": "user-beta"}

    # User A burns all 5 tokens
    for _ in range(5):
        assert client.get("/api/v1/resource", headers=headers_user_a).status_code == 200

    # User A is throttled
    assert client.get("/api/v1/resource", headers=headers_user_a).status_code == 429

    # User B should still have a full bucket of 5 tokens
    res_b = client.get("/api/v1/resource", headers=headers_user_b)
    assert res_b.status_code == 200
    assert res_b.headers["X-RateLimit-Remaining"] == "4"

def test_documentation_paths_are_exempt():
    """Verify /docs and /openapi.json bypass the limiter entirely."""
    for _ in range(10):
        assert client.get("/docs").status_code == 200
        assert client.get("/openapi.json").status_code == 200