

import os
from fastapi import APIRouter, Query
from typing import List, Optional
import pandas as pd
import pyarrow.dataset as ds
import math

from schemas.models import EarthquakeOut, RunStatsOut

router = APIRouter(prefix="/earthquakes", tags=["earthquakes"])

BACKEND = os.getenv("BACKEND", "parquet").lower()
SILVER_BASE = os.getenv("SILVER_BASE", "./data/silver")

# ---------- Helpers (Parquet backend) ----------
def _events_ds():
    return ds.dataset(f"{SILVER_BASE}/earthquakes", format="parquet", partitioning="hive")

def _stats_ds():
    return ds.dataset(f"{SILVER_BASE}/run_stats", format="parquet", partitioning="hive")

def _recent_parquet(hours: int, min_mag: float, limit: int):
    # simples: lê tudo e filtra; suficiente para MVP
    df = _events_ds().to_table().to_pandas()
    if df.empty:
        return []
    # filtro por magnitude
    df = df[df["mag"].fillna(0) >= float(min_mag)]
    # ordena e limita (time_utc já é datetime64[ns, UTC] vindo do transform)
    df = df.sort_values("time_utc", ascending=False).head(int(limit))
    # serializa
    return df.to_dict(orient="records")

def _latest_run_parquet():
    df = _stats_ds().to_table().to_pandas()
    if df.empty:
        return None
    df = df.sort_values("time_max_utc", ascending=False).head(1)
    return df.iloc[0].to_dict()

# Haversine para /around
def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlambda/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def _around_parquet(lat: float, lon: float, radius_km: float, min_mag: float, limit: int):
    df = _events_ds().to_table().to_pandas()
    if df.empty:
        return []
    df = df.dropna(subset=["lat", "lon"])
    # filtro rápido por mag
    df = df[df["mag"].fillna(0) >= float(min_mag)]
    # calcula distância
    df["dist_km"] = df.apply(lambda r: _haversine_km(lat, lon, float(r["lat"]), float(r["lon"])), axis=1)
    df = df[df["dist_km"] <= float(radius_km)]
    df = df.sort_values(["time_utc"], ascending=False).head(int(limit))
    return df.drop(columns=["dist_km"]).to_dict(orient="records")

# ---------- Endpoints ----------
@router.get("/recent", response_model=List[EarthquakeOut])
def recent(
    hours: int = Query(24, ge=1, le=168),
    min_mag: float = Query(0.0, ge=0.0),
    limit: int = Query(200, ge=1, le=1000),
):
    # Parquet agora; Postgres no futuro
    if BACKEND == "parquet":
        return _recent_parquet(hours, min_mag, limit)
    # TODO: implementar SQL quando Postgres estiver disponível
    return []

@router.get("/around", response_model=List[EarthquakeOut])
def around(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(250.0, gt=0, le=2000),
    min_mag: float = Query(0.0, ge=0.0),
    limit: int = Query(200, ge=1, le=1000),
):
    if BACKEND == "parquet":
        return _around_parquet(lat, lon, radius_km, min_mag, limit)
    # TODO: SQL (usando ST_DWithin em PostGIS no futuro)
    return []

@router.get("/runs/latest", response_model=Optional[RunStatsOut])
def runs_latest():
    if BACKEND == "parquet":
        return _latest_run_parquet()
    # TODO: SQL (SELECT ... ORDER BY time_max_utc DESC LIMIT 1)
    return None

@router.get("/by-date/{date}", response_model=List[EarthquakeOut])
def by_date(date: str):
    """
    Lê diretamente a partição 'date=YYYY-MM-DD'
    """
    try:
        ds_day = ds.dataset(f"{SILVER_BASE}/earthquakes/date={date}", format="parquet")
        df = ds_day.to_table().to_pandas().sort_values("time_utc", ascending=False)
        return df.to_dict(orient="records")
    except Exception:
        return []
