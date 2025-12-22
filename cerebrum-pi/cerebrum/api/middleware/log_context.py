# cerebrum/api/middleware/log_context.py

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging

logger = logging.getLogger("CerebrumCM4")

class LogContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start

        request_id = getattr(request.state, "request_id", "-")

        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"{response.status_code} {duration:.3f}s"
        )

        return response
