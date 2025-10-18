# api/middleware/auth.py
import os
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 1) Liberar docs, schema, redoc e health
        allowlisted = (
            path == "/health"
            or path == "/openapi.json"
            or path.startswith("/docs")
            or path.startswith("/redoc")
            or path.startswith("/static")
        )
        if allowlisted:
            return await call_next(request)

        # 2) Liberar preflight CORS (OPTIONS), senão o browser toma 401
        if request.method.upper() == "OPTIONS":
            return await call_next(request)

        # 3) Verificar chave no header
        expected_key = os.getenv("API_KEY")
        if not expected_key:
            raise HTTPException(status_code=500, detail="API key not configured.")

        provided_key = request.headers.get("X-API-Key")
        if provided_key != expected_key:
            raise HTTPException(status_code=401, detail="Unauthorized: invalid or missing API key.")

        return await call_next(request)
