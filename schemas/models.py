# schemas/models.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class EarthquakeOut(BaseModel):
    event_id: str
    mag: Optional[float] = None
    place: Optional[str] = None
    time_utc: datetime
    lat: Optional[float] = None
    lon: Optional[float] = None
    depth_km: Optional[float] = None
    run_id: Optional[str] = None
    ingestion_time_utc: Optional[datetime] = None

class RunStatsOut(BaseModel):
    run_id: str
    date: Optional[str] = None
    records: Optional[int] = None
    time_min_utc: Optional[datetime] = None
    time_max_utc: Optional[datetime] = None
    bbox_west: Optional[float] = None
    bbox_south: Optional[float] = None
    bbox_min_depth_km: Optional[float] = None
    bbox_east: Optional[float] = None
    bbox_north: Optional[float] = None
    bbox_max_depth_km: Optional[float] = None
