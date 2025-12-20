"""
CM4 VPS Client - Communicates with VPS Backend
==============================================

Handles all communication with the VPS inference backend over Tailscale.
Includes retry logic, timeout handling, and graceful fallbacks.

File: /opt/cerebrum/cerebrum/core/vps_client.py
"""

import os
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger('CerebrumVPS')


class VPSClient:
    """
    Client for communicating with VPS inference backend.
    """

    def __init__(
        self,
        vps_endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 2
    ):
        """
        Initialize VPS client.

        Args:
            vps_endpoint: VPS endpoint URL (e.g., http://100.78.22.113:9000)
            api_key: API key for authentication
            timeout: Request timeout in seconds
            max_retries: Number of retry attempts
        """
        self.endpoint = vps_endpoint or os.getenv(
            "VPS_ENDPOINT", 
            "http://100.78.22.113:9000"
        )
        self.api_key = api_key or os.getenv("VPS_API_KEY", "")
        self.timeout = timeout
        self.max_retries = max_retries

        # Statistics
        self.requests_sent = 0
        self.requests_successful = 0
        self.requests_failed = 0
        self.total_inference_time = 0.0

        # Client
        self._client: Optional[httpx.AsyncClient] = None

        logger.info(f"VPS Client initialized: {self.endpoint}")

    async def __aenter__(self):
        """Async context manager entry"""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._client:
            await self._client.aclose()

    async def check_health(self) -> Dict[str, Any]:
        """
        Check VPS backend health.

        Returns:
            Health status dict
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.endpoint}/health")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"VPS health check failed: {e}")
            return {
                "status": "unavailable",
                "available": False,
                "error": str(e)
            }

    async def is_available(self) -> bool:
        """
        Quick check if VPS is available.

        Returns:
            True if VPS is ready to accept requests
        """
        health = await self.check_health()
        return health.get("available", False)

    async def inference(
        self,
        prompt: str,
        model: str = "qwen_7b",
        max_tokens: int = 512,
        temperature: float = 0.2,
        stop: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Run inference on VPS backend.

        Args:
            prompt: Input prompt
            model: Model name to use
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stop: Stop sequences

        Returns:
            Inference result dict

        Raises:
            VPSUnavailableError: If VPS is unavailable
            VPSInferenceError: If inference fails
        """
        self.requests_sent += 1
        start_time = time.time()

        request_data = {
            "prompt": prompt,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stop": stop or []
        }

        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

        # Retry logic
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.endpoint}/v1/inference",
                        json=request_data,
                        headers=headers
                    )

                    if response.status_code == 200:
                        result = response.json()

                        # Update statistics
                        elapsed = time.time() - start_time
                        self.requests_successful += 1
                        self.total_inference_time += elapsed

                        logger.info(
                            f"VPS inference successful: {model} "
                            f"({result.get('tokens_generated', 0)} tokens in 
{elapsed:.2f}s)"
                        )

                        return result

                    elif response.status_code == 503:
                        # VPS overloaded
                        raise VPSUnavailableError(
                            "VPS is overloaded or busy with iOS backend"
                        )

                    elif response.status_code == 403:
                        # Auth error - don't retry
                        raise VPSInferenceError(
                            "Authentication failed - check VPS_API_KEY"
                        )

                    else:
                        raise VPSInferenceError(
                            f"VPS returned status {response.status_code}: 
{response.text}"
                        )

            except httpx.TimeoutException as e:
                last_error = VPSUnavailableError(f"VPS timeout: {e}")
                if attempt < self.max_retries:
                    logger.warning(f"VPS timeout, retrying ({attempt + 
1}/{self.max_retries})...")
                    await asyncio.sleep(1)
                    continue

            except httpx.ConnectError as e:
                last_error = VPSUnavailableError(f"Cannot connect to VPS: {e}")
                if attempt < self.max_retries:
                    logger.warning(f"VPS connection error, retrying ({attempt + 
1}/{self.max_retries})...")
                    await asyncio.sleep(1)
                    continue

            except VPSUnavailableError as e:
                last_error = e
                # Don't retry if VPS is intentionally rejecting (overloaded)
                break

            except VPSInferenceError as e:
                last_error = e
                # Don't retry on auth errors or other client errors
                break

            except Exception as e:
                last_error = VPSInferenceError(f"Unexpected error: {e}")
                if attempt < self.max_retries:
                    logger.warning(f"Unexpected error, retrying ({attempt + 
1}/{self.max_retries})...")
                    await asyncio.sleep(1)
                    continue

        # All retries failed
        self.requests_failed += 1
        logger.error(f"VPS inference failed after {self.max_retries + 1} attempts: 
{last_error}")
        raise last_error

    async def list_models(self) -> Dict[str, Any]:
        """
        Get list of available models from VPS.

        Returns:
            Models dict
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.endpoint}/v1/models",
                    headers={"X-API-Key": self.api_key}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to list VPS models: {e}")
            return {"available_models": [], "error": str(e)}

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get VPS statistics.

        Returns:
            Stats dict
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.endpoint}/v1/stats",
                    headers={"X-API-Key": self.api_key}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get VPS stats: {e}")
            return {"error": str(e)}

    def get_client_stats(self) -> Dict[str, Any]:
        """
        Get client-side statistics.

        Returns:
            Client stats dict
        """
        avg_time = (
            self.total_inference_time / self.requests_successful
            if self.requests_successful > 0
            else 0.0
        )

        success_rate = (
            (self.requests_successful / self.requests_sent * 100)
            if self.requests_sent > 0
            else 0.0
        )

        return {
            "requests_sent": self.requests_sent,
            "requests_successful": self.requests_successful,
            "requests_failed": self.requests_failed,
            "success_rate_percent": round(success_rate, 2),
            "avg_inference_time_seconds": round(avg_time, 3),
            "total_inference_time_seconds": round(self.total_inference_time, 2)
        }


# Custom exceptions
class VPSUnavailableError(Exception):
    """VPS is unavailable or unreachable"""
    pass


class VPSInferenceError(Exception):
    """VPS inference failed"""
    pass


# Singleton instance (optional)
_vps_client: Optional[VPSClient] = None


def get_vps_client() -> VPSClient:
    """
    Get singleton VPS client instance.

    Returns:
        VPSClient instance
    """
    global _vps_client
    if _vps_client is None:
        _vps_client = VPSClient()
    return _vps_client


# Import asyncio for sleep
import asyncio
                                                   
