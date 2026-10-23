import time
import asyncio
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class BucketState:
    tokens: float
    last_updated: float

class TokenBucketLimiter:
    """
    In-memory, concurrency-safe Token Bucket rate limiter.
    
    :param capacity: Maximum burst size (maximum tokens bucket can hold).
    :param refill_rate: Continuous refill rate (tokens added per second).
    """
    def __init__(self, capacity: float = 10.0, refill_rate: float = 1.0):
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self.buckets: Dict[str, BucketState] = {}
        self._lock = asyncio.Lock()

    async def consume(self, key: str, tokens: float = 1.0) -> Tuple[bool, int, float]:
        """
        Attempts to consume tokens from the bucket associated with the given key.
        
        Returns:
            Tuple[is_allowed (bool), remaining_tokens (int), retry_after_seconds (float)]
        """
        async with self._lock:
            now = time.monotonic()

            # Retrieve existing state or initialize full bucket for new clients
            state = self.buckets.get(key)
            if state is None:
                current_tokens = self.capacity
                last_updated = now
            else:
                elapsed = now - state.last_updated
                # Lazy refill calculation capped at maximum capacity
                refill_amount = elapsed * self.refill_rate
                current_tokens = min(self.capacity, state.tokens + refill_amount)
                last_updated = now

            # Decision logic
            if current_tokens >= tokens:
                new_tokens = current_tokens - tokens
                self.buckets[key] = BucketState(tokens=new_tokens, last_updated=last_updated)
                return True, int(new_tokens), 0.0
            else:
                # Calculate precise time required to accumulate enough tokens for 1 request
                deficit = tokens - current_tokens
                retry_after = deficit / self.refill_rate
                self.buckets[key] = BucketState(tokens=current_tokens, last_updated=last_updated)
                return False, int(current_tokens), round(retry_after, 2)

    async def reset(self):
        """Clears all client bucket records (useful for test isolation)."""
        async with self._lock:
            self.buckets.clear()