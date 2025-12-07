"""Base integration client with common functionality."""

import logging
import time
from datetime import datetime
from typing import Optional, Any
from abc import ABC, abstractmethod

from app.models.base import APICallLog

logger = logging.getLogger(__name__)


class BaseIntegrationClient(ABC):
    """Base class for external service integrations."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
        simulate: bool = True
    ):
        self.api_key = api_key or "PLACEHOLDER_API_KEY"
        self.base_url = base_url or ""
        self.timeout = timeout
        self.simulate = simulate
        self.call_logs: list[APICallLog] = []
    
    @property
    @abstractmethod
    def service_name(self) -> str:
        """Return the service name for logging."""
        pass
    
    def _log_api_call(
        self,
        endpoint: str,
        method: str,
        request_payload: dict,
        response_payload: Optional[dict],
        status_code: int,
        latency_ms: float,
        error: Optional[str] = None
    ) -> APICallLog:
        """Log an API call for audit purposes."""
        log = APICallLog(
            service_name=self.service_name,
            endpoint=endpoint,
            method=method,
            request_payload=self._sanitize_payload(request_payload),
            response_payload=response_payload,
            status_code=status_code,
            latency_ms=latency_ms,
            error=error
        )
        self.call_logs.append(log)
        
        logger.info(
            f"API Call: {self.service_name} {method} {endpoint} "
            f"status={status_code} latency={latency_ms:.2f}ms"
        )
        
        return log
    
    def _sanitize_payload(self, payload: dict) -> dict:
        """Remove sensitive data from payload for logging."""
        sensitive_keys = {"api_key", "password", "token", "secret", "audio_data"}
        sanitized = {}
        
        for key, value in payload.items():
            if key.lower() in sensitive_keys:
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_payload(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _simulate_latency(self, base_ms: float = 100, variance_ms: float = 50) -> float:
        """Simulate realistic API latency."""
        import random
        latency = base_ms + random.uniform(-variance_ms, variance_ms)
        time.sleep(latency / 1000)
        return latency
    
    def get_call_logs(self) -> list[APICallLog]:
        """Get all API call logs."""
        return self.call_logs
    
    def clear_call_logs(self):
        """Clear API call logs."""
        self.call_logs = []
