import asyncio
import time
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class RateLimitStatus:
    """GitHub API rate limit status"""
    limit: int = 5000
    remaining: int = 5000
    reset_time: int = 0
    used: int = 0
    
    @property
    def reset_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.reset_time)
    
    @property
    def seconds_until_reset(self) -> float:
        return max(0, self.reset_time - time.time())
    
    @property
    def is_exhausted(self) -> bool:
        return self.remaining <= 0

class RateLimiter:
    """Intelligent GitHub API rate limiter"""
    
    def __init__(self, config):
        self.config = config
        self.status = RateLimitStatus()
        self.logger = logging.getLogger(__name__)
        self.request_times = []  # Track request timing
        self.consecutive_failures = 0
        self.conservative_mode = False
        
    def update_from_headers(self, headers: Dict[str, str]) -> None:
        """Update rate limit status from response headers"""
        try:
            self.status.limit = int(headers.get('X-RateLimit-Limit', 5000))
            self.status.remaining = int(headers.get('X-RateLimit-Remaining', 5000))
            self.status.reset_time = int(headers.get('X-RateLimit-Reset', time.time() + 3600))
            self.status.used = int(headers.get('X-RateLimit-Used', 0))
            
            # Reset consecutive failures on successful rate limit update
            self.consecutive_failures = 0
            
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Failed to parse rate limit headers: {e}")
    
    def is_safe_to_proceed(self, upcoming_requests: int = 1) -> bool:
        """Check if it's safe to make upcoming requests"""
        buffer = self.config.rate_limit_buffer
        
        # Conservative mode uses larger buffer
        if self.conservative_mode:
            buffer *= 2
            
        return self.status.remaining > (upcoming_requests + buffer)
    
    def calculate_delay(self, upcoming_requests: int = 1) -> float:
        """Calculate appropriate delay before next request"""
        
        # If we're safe, minimal delay
        if self.is_safe_to_proceed(upcoming_requests):
            return self._calculate_minimal_delay()
        
        # If rate limit exhausted, wait for reset
        if self.status.is_exhausted:
            return self.status.seconds_until_reset + 60  # 1 minute buffer
        
        # If approaching limit, calculate proportional delay
        remaining_time = self.status.seconds_until_reset
        requests_needed = upcoming_requests + self.config.rate_limit_buffer
        
        if requests_needed >= self.status.remaining:
            # Not enough requests left, wait for reset
            return remaining_time + 60
        
        # Spread remaining requests over remaining time
        return max(0.5, remaining_time / self.status.remaining)
    
    def _calculate_minimal_delay(self) -> float:
        """Calculate minimal delay to avoid overwhelming API"""
        # Clean old request times (keep last minute)
        current_time = time.time()
        self.request_times = [
            req_time for req_time in self.request_times 
            if current_time - req_time < 60
        ]
        
        # If too many requests in last minute, slow down
        if len(self.request_times) > 60:  # More than 1 per second
            return 1.0
        elif len(self.request_times) > 30:  # More than 0.5 per second
            return 0.5
        else:
            return 0.1  # Minimal delay
    
    async def wait_if_needed(self, upcoming_requests: int = 1) -> None:
        """Wait if necessary before making request"""
        delay = self.calculate_delay(upcoming_requests)
        
        if delay > 60:  # Long delay, inform user
            reset_time = self.status.reset_datetime.strftime('%H:%M:%S')
            self.logger.info(
                f"Rate limit approaching. Waiting {delay/60:.1f} minutes "
                f"(resets at {reset_time})"
            )
        
        if delay > 0:
            await asyncio.sleep(delay)
    
    def record_request(self) -> None:
        """Record that a request was made"""
        self.request_times.append(time.time())
    
    def handle_rate_limit_error(self, response_headers: Dict[str, str]) -> float:
        """Handle 403 rate limit exceeded response"""
        self.consecutive_failures += 1
        self.update_from_headers(response_headers)
        
        # Enable conservative mode after multiple failures
        if self.consecutive_failures >= 3:
            self.conservative_mode = True
            self.logger.warning("Enabling conservative mode due to repeated rate limit hits")
        
        wait_time = self.status.seconds_until_reset + 120  # 2 minute buffer
        self.logger.error(
            f"Rate limit exceeded! Waiting {wait_time/60:.1f} minutes until reset"
        )
        return wait_time
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get current rate limit status for display"""
        return {
            'remaining': self.status.remaining,
            'limit': self.status.limit,
            'reset_time': self.status.reset_datetime.strftime('%H:%M:%S'),
            'seconds_until_reset': int(self.status.seconds_until_reset),
            'conservative_mode': self.conservative_mode,
            'usage_percentage': ((self.status.limit - self.status.remaining) / self.status.limit) * 100
        }