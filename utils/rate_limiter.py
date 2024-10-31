import time
from typing import Dict, Optional
from datetime import datetime, timedelta
import threading

class RateLimiter:
    """Rate limiter using token bucket algorithm"""
    
    def __init__(
        self,
        tokens_per_second: float,
        bucket_size: int
    ):
        self.tokens_per_second = tokens_per_second
        self.bucket_size = bucket_size
        self.tokens = bucket_size
        self.last_update = time.time()
        self.lock = threading.Lock()
    
    def _add_tokens(self) -> None:
        """Add tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_update
        new_tokens = elapsed * self.tokens_per_second
        self.tokens = min(self.bucket_size, self.tokens + new_tokens)
        self.last_update = now
    
    def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """Acquire tokens from the bucket"""
        start_time = time.time()
        
        while True:
            with self.lock:
                self._add_tokens()
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
                
                if timeout is not None:
                    if time.time() - start_time >= timeout:
                        return False
            
            time.sleep(0.1)

class APIRateLimiter:
    """Rate limiter for API calls"""
    
    def __init__(self):
        self.limiters: Dict[str, RateLimiter] = {
            'claude': RateLimiter(5, 10),  # 5 requests per second, bucket size 10
            'tavily': RateLimiter(2, 5),   # 2 requests per second, bucket size 5
        }
    
    def acquire(self, api_name: str, tokens: int = 1) -> bool:
        """Acquire tokens for specific API"""
        if api_name not in self.limiters:
            return True
        return self.limiters[api_name].acquire(tokens) 