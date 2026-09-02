import time
import threading

class RateLimiter:
    """Token-bucket rate limiter for API requests."""
    def __init__(self, max_tokens: int = 10, refill_rate_per_sec: float = 2.0):
        self.max_tokens = max_tokens
        self.tokens = float(max_tokens)
        self.refill_rate = refill_rate_per_sec
        self.last_refill = time.time()
        self.lock = threading.Lock()

    def acquire(self, tokens_requested: int = 1) -> bool:
        with self.lock:
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(float(self.max_tokens), self.tokens + elapsed * self.refill_rate)
            self.last_refill = now

            if self.tokens >= tokens_requested:
                self.tokens -= tokens_requested
                return True
            return False

# Global instance for third-party API rate control
global_rate_limiter = RateLimiter(max_tokens=20, refill_rate_per_sec=5.0)
