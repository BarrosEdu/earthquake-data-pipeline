
import math
from fastapi import APIRouter, Query
from typing import List, Optional
from sqlalchemy import text
from api.db import SessionLocal
from schemas.models import EarthquakeOut

router = APIRouter(prefix="/earthquakes", tags=["earthquakes"])

@router.get("/recent", response_model=List[EarthquakeOut])
def recent(hours: int = 24, min_mag: float = 0.0, limit: int = 100):
    
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
