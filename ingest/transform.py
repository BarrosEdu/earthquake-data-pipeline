import pandas as pd
import json, os
import pytz

from fecth_data import ingest_to_bronze

def transform_to_silver(bronze_base):
    # load raw and manifest
    with open(f'{bronze_base}/usgs_all_hour.geojson') as f:
        data = json.load(f)
    with open(f'{bronze_base}/_manifest.json') as f:
        manifest = json.load(f)

    features = data.get("features", [])
    if not features:
        return None

    df = pd.json_normalize(features)

    #Transformation process - cleaning data and creating new columns

 
    df['event_id'] = df['id']
    df['mag'] = df['properties.mag']
    df['place'] = df['properties.place']
    df['time_utc'] = pd.to_datetime(df['properties.time'], unit='ms', utc=True)
    df['updated_utc'] = pd.to_datetime(df['properties.updated'], unit='ms', utc=True)

    # timezone local (Asia/Dubai)
    tz_local = pytz.timezone('Asia/Dubai')
    df['time_local'] = df['time_utc'].dt.tz_convert(tz_local)
    df['updated_local'] = df['updated_utc'].dt.tz_convert(tz_local)

    # coordinates
    coords = df['geometry.coordinates'].apply(pd.Series)
    df['lon'] = coords[0]
    df['lat'] = coords[1]
    df['depth_km'] = coords[2]

    # metadados
    df['source'] = 'USGS'
    df['run_id'] = manifest['run_id']
    df['ingestion_time_utc'] = pd.to_datetime(manifest['ingestion_time_utc'])

    # Selecting columns to be used in MVP
    cols = [
        'event_id', 'mag', 'place',
        'time_utc', 'time_local',
        'updated_utc', 'updated_local',
        'lat', 'lon', 'depth_km',
        'source', 'run_id', 'ingestion_time_utc'
    ]
    df = df[cols].sort_values(['time_utc', 'event_id'])

    # dedup Snapshot (latest)
    df = df.sort_values(['event_id', 'updated_utc']).drop_duplicates('event_id', keep='last')

    # salve parquet partition by date
    date_part = df['time_utc'].dt.date.astype(str).iloc[0] 
    outdir = f'./data/silver/earthquakes/date={date_part}'
    os.makedirs(outdir, exist_ok=True)
    df.to_parquet(f'{outdir}/data.parquet', index=False)

    # -----------------------------
    # STATS (run-level) com BBOX
    # -----------------------------
    bbox = manifest.get("bbox")
    if bbox:
        west, south, dmin, east, north, dmax = bbox
    else:
        west, east  = float(df["lon"].min()), float(df["lon"].max())
        south, north= float(df["lat"].min()), float(df["lat"].max())
        dmin, dmax  = float(df["depth_km"].min()), float(df["depth_km"].max())

    stats = pd.DataFrame([{
        "run_id": manifest["run_id"],
        "date": date_part,
        "records": int(manifest.get("records", len(df))),
        "time_min_utc": df["time_utc"].min(),
        "time_max_utc": df["time_utc"].max(),
        "bbox_west": west, "bbox_south": south, "bbox_min_depth_km": dmin,
        "bbox_east": east, "bbox_north": north, "bbox_max_depth_km": dmax,
    }])

    stats_dir = f'./data/silver/run_stats/date={date_part}/run_id={manifest["run_id"]}'
    os.makedirs(stats_dir, exist_ok=True)
    stats.to_parquet(f'{stats_dir}/stats.parquet', index=False)

    return {"rows": len(df), "outdir": outdir, "statsdir": stats_dir}

# Data Flow
if __name__ == "__main__":
    bronze_info = ingest_to_bronze()
    transform_to_silver(bronze_info['base'])
