
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from api.routers import earthquakes_db as earthquakes
from api.middleware.auth import APIKeyMiddleware
from fastapi.openapi.utils import get_openapi

load_dotenv()

app = FastAPI(
    title="Earthquakes API",
    version="0.1",
    description="MVP - Earthquake data from USGS stored on Postgres/PostGIS with a simple REST API."
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

# Middleware - API Key 
app.add_middleware(APIKeyMiddleware)


app.include_router(earthquakes.router)

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
