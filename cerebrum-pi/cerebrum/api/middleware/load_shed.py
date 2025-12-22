# cerebrum/api/middleware/load_shed.py

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

class LoadSheddingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_inflight: int = 2):
        super().__init__(app)
        self._inflight = 0
        self._max = max_inflight

    async def dispatch(self, request: Request, call_next):
        if self._inflight >= self._max:
            return JSONResponse(  # Changed from raise HTTPException
                status_code=503,
                content={
                    "error": "CM4 busy",
                    "message": "Too many concurrent requests, retry shortly"
                }
            )

        self._inflight += 1
        try:
            return await call_next(request)
        finally:
            self._inflight -= 1
