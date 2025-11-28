import os
import time

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware

from api.routers import earthquakes_db as earthquakes
from api.middleware.auth import APIKeyMiddleware

# NOVO: Prometheus puro (sem Instrumentator)
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST


load_dotenv()

app = FastAPI(
    title="Earthquakes API",
    version="0.1",
    description="MVP - Earthquake data from USGS stored on Postgres/PostGIS with a simple REST API.",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Healthcheck - Don't need auth
@app.get("/health")
def health():
    return {"status": "ok"}


# =========================
# MÉTRICAS PROMETHEUS
# =========================

# Contador de requisições por método, path e status code
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

# Latência por método e path
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        process_time = time.time() - start_time
        path = request.url.path
        method = request.method
        status = response.status_code

        # registra métricas
        REQUEST_COUNT.labels(method=method, path=path, status=status).inc()
        REQUEST_LATENCY.labels(method=method, path=path).observe(process_time)

        return response


# Adiciona o middleware de métricas
app.add_middleware(MetricsMiddleware)


# Endpoint /metrics em formato Prometheus
@app.get("/metrics")
def metrics():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


# --- Swagger: with API Key
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema.setdefault("components", {}).setdefault("securitySchemes", {})
    schema["components"]["securitySchemes"]["ApiKeyAuth"] = {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
    }
    schema["security"] = [{"ApiKeyAuth": []}]
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi
app.swagger_ui_parameters = {"persistAuthorization": True}
