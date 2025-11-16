"""
Unified LLM Router

Routes LLM requests to appropriate backend (Ollama, MLX, etc.) based on
admin configuration. Supports per-model backend selection with automatic
fallback.

Open Source Compatible - No vendor lock-in.
"""
import os
import httpx
import time
from typing import Dict, Any, Optional, List
from enum import Enum
from collections import deque
import structlog

logger = structlog.get_logger()


class BackendType(str, Enum):
    """Supported LLM backend types."""
    OLLAMA = "ollama"
    MLX = "mlx"
    AUTO = "auto"  # Try MLX first, fall back to Ollama


class LLMRouter:
    """
    Routes LLM requests to configured backends.

    Usage:
        router = LLMRouter(admin_url="http://localhost:8080")
        response = await router.generate(
            model="phi3:mini",
            prompt="Hello world",
            temperature=0.7
        )
    """

    def __init__(
        self,
        admin_url: Optional[str] = None,
        cache_ttl: int = 60,
        metrics_window_size: int = 100,
        persist_metrics: bool = True
    ):
        """
        Initialize LLM Router.

        Args:
            admin_url: Admin API URL for fetching backend configs
            cache_ttl: Cache TTL in seconds for backend configs
            metrics_window_size: Number of recent requests to track for metrics
            persist_metrics: Whether to persist metrics to database via Admin API
        """
        self.admin_url = admin_url or os.getenv(
            "ADMIN_API_URL",
            "http://localhost:8080"
        )
        self._admin_url_base = self.admin_url
        self.client = httpx.AsyncClient(timeout=120.0)
        self._backend_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_expiry: Dict[str, float] = {}
        self._cache_ttl = cache_ttl
        self._persist_metrics = persist_metrics

        # Performance metrics storage (rolling window)
        self._metrics_window_size = metrics_window_size
        self._metrics: deque = deque(maxlen=metrics_window_size)
        logger.info(
            "llm_router_initialized",
            metrics_window_size=metrics_window_size,
            persist_metrics=persist_metrics
        )

    async def _get_backend_config(self, model: str) -> Dict[str, Any]:
        """
        Fetch backend configuration for a model from admin API.

        Caches results for performance.

        Args:
            model: Model name (e.g., "phi3:mini")

        Returns:
            Backend configuration dict
        """
        now = time.time()

        # Check cache
        if model in self._backend_cache:
            if now < self._cache_expiry.get(model, 0):
                return self._backend_cache[model]

        # Fetch from admin API
        try:
            url = f"{self.admin_url}/api/llm-backends/model/{model}"
            response = await self.client.get(url)

            if response.status_code == 404:
                # No config found - use default Ollama
                logger.warning(
                    "no_backend_config_found",
                    model=model,
                    falling_back="ollama"
                )
                config = {
                    "backend_type": "ollama",
                    "endpoint_url": "http://localhost:11434",
                    "max_tokens": 2048,
                    "temperature_default": 0.7,
                    "timeout_seconds": 60
                }
            else:
                response.raise_for_status()
                config = response.json()

            # Cache
            self._backend_cache[model] = config
            self._cache_expiry[model] = now + self._cache_ttl

            return config

        except Exception as e:
            logger.error(
                "failed_to_fetch_backend_config",
                model=model,
                error=str(e)
            )
            # Fall back to Ollama
            return {
                "backend_type": "ollama",
                "endpoint_url": "http://localhost:11434",
                "max_tokens": 2048,
                "temperature_default": 0.7,
                "timeout_seconds": 60
            }

    async def generate(
        self,
        model: str,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        zone: Optional[str] = None,
        intent: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate text using configured backend for the model.

        Args:
            model: Model name (e.g., "phi3:mini")
            prompt: Input prompt
            temperature: Temperature override
            max_tokens: Max tokens override
            request_id: Optional request ID for tracking
            session_id: Optional session ID for conversation tracking
            user_id: Optional user ID for user-specific analytics
            zone: Optional zone/location for geographic analytics
            intent: Optional intent classification for categorization
            **kwargs: Additional backend-specific parameters

        Returns:
            Generated response with metadata
        """
        # Get backend configuration
        config = await self._get_backend_config(model)
        backend_type = config["backend_type"]
        endpoint_url = config["endpoint_url"]

        # Apply defaults from config
        temperature = temperature or config.get("temperature_default", 0.7)
        max_tokens = max_tokens or config.get("max_tokens", 2048)
        timeout = config.get("timeout_seconds", 60)

        logger.info(
            "routing_llm_request",
            model=model,
            backend_type=backend_type,
            endpoint=endpoint_url
        )

        start_time = time.time()
        response = None

        try:
            if backend_type == BackendType.AUTO:
                # Try MLX first, fall back to Ollama
                try:
                    response = await self._generate_mlx(
                        endpoint_url, model, prompt, temperature, max_tokens, timeout
                    )
                except Exception as e:
                    logger.warning(
                        "mlx_failed_falling_back_to_ollama",
                        error=str(e)
                    )
                    # Fall back to Ollama
                    ollama_url = "http://localhost:11434"
                    response = await self._generate_ollama(
                        ollama_url, model, prompt, temperature, max_tokens, timeout
                    )

            elif backend_type == BackendType.MLX:
                response = await self._generate_mlx(
                    endpoint_url, model, prompt, temperature, max_tokens, timeout
                )

            else:  # OLLAMA
                response = await self._generate_ollama(
                    endpoint_url, model, prompt, temperature, max_tokens, timeout
                )

            return response

        finally:
            duration = time.time() - start_time

            # Track metrics if response was generated
            if response:
                tokens = response.get("eval_count", 0)
                tokens_per_sec = tokens / duration if duration > 0 and tokens > 0 else 0

                metric = {
                    "timestamp": start_time,
                    "model": model,
                    "backend": response.get("backend"),
                    "latency_seconds": duration,
                    "tokens": tokens,
                    "tokens_per_second": tokens_per_sec,
                    "request_id": request_id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "zone": zone,
                    "intent": intent
                }
                self._metrics.append(metric)

                # Persist metric to database asynchronously
                import asyncio
                asyncio.create_task(self._persist_metric(metric))

                logger.info(
                    "llm_request_completed",
                    model=model,
                    backend_type=backend_type,
                    duration=duration,
                    tokens_per_sec=round(tokens_per_sec, 2),
                    request_id=request_id,
                    session_id=session_id
                )
            else:
                logger.info(
                    "llm_request_completed",
                    model=model,
                    backend_type=backend_type,
                    duration=duration,
                    request_id=request_id,
                    session_id=session_id
                )

    async def _generate_ollama(
        self,
        endpoint_url: str,
        model: str,
        prompt: str,
        temperature: float,
        max_tokens: int,
        timeout: int
    ) -> Dict[str, Any]:
        """Generate using Ollama backend."""
        client = httpx.AsyncClient(base_url=endpoint_url, timeout=timeout)

        try:
            response = await client.post("/api/generate", json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            })

            response.raise_for_status()
            data = response.json()

            return {
                "response": data.get("response"),
                "backend": "ollama",
                "model": model,
                "done": data.get("done", True),
                "total_duration": data.get("total_duration"),
                "eval_count": data.get("eval_count")
            }

        finally:
            await client.aclose()

    async def _generate_mlx(
        self,
        endpoint_url: str,
        model: str,
        prompt: str,
        temperature: float,
        max_tokens: int,
        timeout: int
    ) -> Dict[str, Any]:
        """Generate using MLX backend."""
        client = httpx.AsyncClient(base_url=endpoint_url, timeout=timeout)

        try:
            # MLX server uses OpenAI-compatible API
            response = await client.post("/v1/completions", json={
                "model": model,
                "prompt": prompt,
                "temperature": temperature,
                "max_tokens": max_tokens
            })

            response.raise_for_status()
            data = response.json()

            choice = data["choices"][0]

            return {
                "response": choice["text"],
                "backend": "mlx",
                "model": model,
                "done": True,
                "total_duration": None,  # MLX doesn't provide this
                "eval_count": data.get("usage", {}).get("completion_tokens")
            }

        finally:
            await client.aclose()

    async def _persist_metric(self, metric: Dict[str, Any]):
        """
        Persist metric to database via Admin API.

        Args:
            metric: Metric data to persist

        Note:
            Failures are logged but don't raise exceptions to avoid
            impacting LLM request processing.
        """
        if not self._persist_metrics:
            return

        try:
            url = f"{self._admin_url_base}/api/llm-backends/metrics"
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=metric, timeout=5.0)
                if response.status_code != 201:
                    logger.warning(
                        "failed_to_persist_metric",
                        status_code=response.status_code,
                        error=response.text
                    )
        except Exception as e:
            logger.error("metric_persistence_error", error=str(e))

    def report_metrics(self) -> Dict[str, Any]:
        """
        Report aggregated performance metrics from rolling window.

        Returns:
            Dict with overall and per-model metrics including:
            - avg_latency_seconds: Average request latency
            - avg_tokens_per_second: Average token generation speed
            - total_requests: Number of requests tracked
            - by_model: Per-model breakdown
            - by_backend: Per-backend breakdown
        """
        if not self._metrics:
            return {
                "total_requests": 0,
                "avg_latency_seconds": 0.0,
                "avg_tokens_per_second": 0.0,
                "by_model": {},
                "by_backend": {}
            }

        # Overall metrics
        total_requests = len(self._metrics)
        total_latency = sum(m["latency_seconds"] for m in self._metrics)
        total_tokens_per_sec = sum(m["tokens_per_second"] for m in self._metrics if m["tokens_per_second"] > 0)
        requests_with_tokens = sum(1 for m in self._metrics if m["tokens_per_second"] > 0)

        avg_latency = total_latency / total_requests if total_requests > 0 else 0.0
        avg_tokens_per_sec = total_tokens_per_sec / requests_with_tokens if requests_with_tokens > 0 else 0.0

        # Per-model metrics
        by_model: Dict[str, Dict[str, Any]] = {}
        for metric in self._metrics:
            model = metric["model"]
            if model not in by_model:
                by_model[model] = {
                    "requests": 0,
                    "total_latency": 0.0,
                    "total_tokens_per_sec": 0.0,
                    "requests_with_tokens": 0
                }

            by_model[model]["requests"] += 1
            by_model[model]["total_latency"] += metric["latency_seconds"]
            if metric["tokens_per_second"] > 0:
                by_model[model]["total_tokens_per_sec"] += metric["tokens_per_second"]
                by_model[model]["requests_with_tokens"] += 1

        # Calculate averages for each model
        for model, stats in by_model.items():
            stats["avg_latency_seconds"] = stats["total_latency"] / stats["requests"]
            stats["avg_tokens_per_second"] = (
                stats["total_tokens_per_sec"] / stats["requests_with_tokens"]
                if stats["requests_with_tokens"] > 0 else 0.0
            )
            # Remove intermediate totals
            del stats["total_latency"]
            del stats["total_tokens_per_sec"]
            del stats["requests_with_tokens"]

        # Per-backend metrics
        by_backend: Dict[str, Dict[str, Any]] = {}
        for metric in self._metrics:
            backend = metric["backend"]
            if backend not in by_backend:
                by_backend[backend] = {
                    "requests": 0,
                    "total_latency": 0.0,
                    "total_tokens_per_sec": 0.0,
                    "requests_with_tokens": 0
                }

            by_backend[backend]["requests"] += 1
            by_backend[backend]["total_latency"] += metric["latency_seconds"]
            if metric["tokens_per_second"] > 0:
                by_backend[backend]["total_tokens_per_sec"] += metric["tokens_per_second"]
                by_backend[backend]["requests_with_tokens"] += 1

        # Calculate averages for each backend
        for backend, stats in by_backend.items():
            stats["avg_latency_seconds"] = stats["total_latency"] / stats["requests"]
            stats["avg_tokens_per_second"] = (
                stats["total_tokens_per_sec"] / stats["requests_with_tokens"]
                if stats["requests_with_tokens"] > 0 else 0.0
            )
            # Remove intermediate totals
            del stats["total_latency"]
            del stats["total_tokens_per_sec"]
            del stats["requests_with_tokens"]

        return {
            "total_requests": total_requests,
            "avg_latency_seconds": round(avg_latency, 3),
            "avg_tokens_per_second": round(avg_tokens_per_sec, 2),
            "by_model": by_model,
            "by_backend": by_backend,
            "window_size": self._metrics_window_size
        }

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# Singleton instance
_router: Optional[LLMRouter] = None


def get_llm_router() -> LLMRouter:
    """Get or create LLM router singleton."""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
