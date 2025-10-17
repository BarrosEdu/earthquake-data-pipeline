
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
#from api.routers import earthquakes
from api.routers import earthquakes_db as earthquakes

app = FastAPI(
    title="Earthquakes API",
    version="0.1",
    description="MVP - API simple data from USGS using Postgres as database"
)

# CORS básico (ajuste se necessário)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

# Rotas
app.include_router(earthquakes.router)
