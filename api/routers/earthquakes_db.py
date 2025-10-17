# api/routers/earthquakes_db.py
import math
from fastapi import APIRouter, Query
from typing import List, Optional
from sqlalchemy import text
from api.db import SessionLocal
from schemas.models import EarthquakeOut

router = APIRouter(prefix="/earthquakes", tags=["earthquakes"])

def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlambda/2)**2
    return 2 * R * math.asin(math.sqrt(a))

@router.get("/recent", response_model=List[EarthquakeOut])
def recent(hours: int = 24, min_mag: float = 0.0, limit: int = 100):
    """
    Retorna terremotos das últimas N horas.
    """
    with SessionLocal() as s:
        q = text("""
          SELECT event_id, mag, place, time_utc, lat, lon, depth_km, run_id, ingestion_time_utc
            FROM earthquakes
           WHERE time_utc >= NOW() - (:hours || ' hours')::interval
             AND (mag IS NULL OR mag >= :min_mag)
           ORDER BY time_utc DESC
           LIMIT :limit
        """)
        rows = s.execute(q, {"hours": hours, "min_mag": min_mag, "limit": limit}).mappings().all()
        return [dict(r) for r in rows]

@router.get("/around", response_model=List[EarthquakeOut])
def around(lat: float, lon: float, radius_km: float = 300.0,
          min_mag: float = 0.0, limit: int = 100):
    from sqlalchemy import text
    radius_m = radius_km * 1000.0
    with SessionLocal() as s:
        q = text("""
          SELECT event_id, mag, place, time_utc, lat, lon, depth_km, run_id, ingestion_time_utc
            FROM earthquakes
           WHERE (mag IS NULL OR mag >= :min_mag)
             AND geom IS NOT NULL
             AND ST_DWithin(
                   geom,
                   ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                   :radius_m
                 )
           ORDER BY time_utc DESC
           LIMIT :limit
        """)
        rows = s.execute(q, {
            "min_mag": min_mag, "lat": lat, "lon": lon,
            "radius_m": radius_m, "limit": limit
        }).mappings().all()
        return [dict(r) for r in rows]
