"""
MinerU Client — 智能限流与重试模块

特性:
  - 令牌桶 (Token Bucket) 速率控制
  - 指数退避 + 随机抖动 (Exponential Backoff + Jitter)
  - 自动识别 Retry-After 响应头
  - 并发安全（线程锁）
"""

import time
import random
import threading
from typing import Optional
from .exceptions import RateLimitError


class TokenBucket:
    """线程安全的令牌桶限流器。

    Args:
        rate: 每秒允许的请求数。
        burst: 突发容量（最大令牌数）。
    """

    def __init__(self, rate: float = 5.0, burst: int = 10):
        self.rate = rate
        self.burst = burst
        self._tokens = float(burst)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """尝试获取令牌。

        Returns:
            True 若获取成功，超时返回 False。
        """
        deadline = time.monotonic() + timeout if timeout else None
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True

            if deadline and time.monotonic() >= deadline:
                return False
            # 等待至少一个令牌的补充时间
            wait = max(0.01, (tokens - self._tokens) / self.rate)
            time.sleep(min(wait, 0.2))

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
        self._last_refill = now


class RetryController:
    """指数退避重试控制器。

    Args:
        max_retries: 最大重试次数。
        base_delay: 基础等待秒数。
        max_delay: 最大等待秒数。
        backoff_factor: 退避倍数。
        jitter: 是否添加随机抖动。
    """

    def __init__(
        self,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter

    def delay_for_attempt(self, attempt: int) -> float:
        """计算第 attempt 次重试应等待的秒数。"""
        delay = self.base_delay * (self.backoff_factor ** attempt)
        delay = min(delay, self.max_delay)
        if self.jitter:
            delay *= random.uniform(0.75, 1.25)
        return delay

    def should_retry(self, attempt: int, status_code: int) -> bool:
        """判断是否应该重试。

        - 429 (Rate Limit): 总是重试，直到 max_retries
        - 5xx: 重试
        - 4xx (except 429): 不重试
        """
        if attempt >= self.max_retries:
            return False
        if status_code == 429:
            return True
        if 500 <= status_code < 600:
            return True
        return False


class RateLimiter:
    """组合限流 + 重试的完整控制器。

    Usage:
        limiter = RateLimiter(requests_per_second=3, max_retries=5)
        with limiter:
            response = requests.post(...)
        # 或手动:
        limiter.wait_before_call()
        response = requests.post(...)
    """

    def __init__(
        self,
        requests_per_second: float = 5.0,
        burst: int = 10,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
    ):
        self.bucket = TokenBucket(rate=requests_per_second, burst=burst)
        self.retry = RetryController(
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
        )

    def wait_before_call(self, timeout: float = 30.0):
        """在发起请求前等待令牌。"""
        if not self.bucket.acquire(timeout=timeout):
            raise RateLimitError(
                f"Rate limiter: unable to acquire token within {timeout}s"
            )

    def handle_response(self, attempt: int, status_code: int, headers) -> float:
        """检查响应并返回建议等待秒数。若不应重试则抛出异常。

        Raises:
            RateLimitError: 当超限或不应重试时。
        """
        if not self.retry.should_retry(attempt, status_code):
            raise RateLimitError(
                f"Request failed with status {status_code}, "
                f"not retrying after {attempt + 1} attempts"
            )

        # 优先使用服务端建议的 Retry-After
        retry_after = headers.get("Retry-After") or headers.get("retry-after")
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                pass

        return self.retry.delay_for_attempt(attempt)

    def __enter__(self):
        self.wait_before_call()
        return self

    def __exit__(self, *args):
        pass
