import pandas as pd
import requests
import json
from datetime import datetime, timezone

USGS_FEED = 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson'

def get_bbox():
    response = requests.get(USGS_FEED)
    response.raise_for_status()
    data = response.json()
    bbox = data["bbox"]
    return bbox

bbox = get_bbox()

# Converte em DataFrame com nomes claros
df = pd.DataFrame([{
    "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
    "ingestion_time_utc": datetime.now(timezone.utc).isoformat(),
    "bbox_west": bbox[0],
    "bbox_south": bbox[1],
    "bbox_min_depth_km": bbox[2],
    "bbox_east": bbox[3],
    "bbox_north": bbox[4],
    "bbox_max_depth_km": bbox[5],
    }])

print(df)
