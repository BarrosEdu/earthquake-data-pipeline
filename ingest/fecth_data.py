import os, json, uuid, requests, pandas as pd
from datetime import datetime, timezone

USGS_FEED = 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson'

def ingest_to_bronze():
    # 1) baixa
    r = requests.get(USGS_FEED, timeout=30)
    r.raise_for_status()
    data = r.json()

    # 2) metadados
    ingestion_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    day = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    # 3) paths
    base = f'./data/bronze/usgs/date={day}/run_id={run_id}'
    os.makedirs(base, exist_ok=True)

    # 4) salva raw
    with open(f'{base}/usgs_all_hour.geojson', 'w') as f:
        json.dump(data, f)

    # 5) salva manifest
    manifest = {
        "source": "USGS all_hour",
        "source_url": USGS_FEED,
        "ingestion_time_utc": ingestion_time,
        "run_id": run_id,
        "records": len(data.get("features", [])),
        "bbox": data.get("bbox")
    }
    with open(f'{base}/_manifest.json', 'w') as f:
        json.dump(manifest, f)

    return {"base": base, **manifest}

