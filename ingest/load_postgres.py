
import os
import pandas as pd
import pyarrow.dataset as ds
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import text
from api.db import engine
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()

SILVER_BASE = os.getenv("SILVER_BASE", "./data/silver")
SOURCE = "USGS"


def _latest_stats_parquet():
    import glob
    paths = sorted(glob.glob(f"{SILVER_BASE}/run_stats/date=*/run_id=*/stats.parquet"))
    if not paths:
        raise FileNotFoundError("Nenhum stats.parquet encontrado em run_stats/")
    return paths[-1]

stats_parquet = _latest_stats_parquet()

# Extract the latest RUN_DATE e RUN_ID do path
parts = stats_parquet.split("/")
RUN_DATE = parts[-3].split("=")[1]
RUN_ID = parts[-2].split("=")[1]


def upsert_ingestion_run(stats_path: str):
    df_stats = ds.dataset(stats_path, format="parquet").to_table().to_pandas()
    assert len(df_stats) == 1, "Esperado apenas 1 linha em stats.parquet"
    rec = df_stats.iloc[0].to_dict()
    rec["run_id"] = RUN_ID
    rec["source"] = SOURCE
    rec["inserted_at_utc"] = datetime.now(timezone.utc)

    cols = ",".join(rec.keys())
    vals = ":" + ", :".join(rec.keys())
    updates = ", ".join([f"{k}=EXCLUDED.{k}" for k in rec.keys() if k != "run_id"])

    with engine.begin() as conn:
        conn.execute(text(f"""
            INSERT INTO ingestion_runs ({cols})
            VALUES ({vals})
            ON CONFLICT (run_id) DO UPDATE SET {updates}
        """), rec)

def upsert_earthquakes(eq_parquet_path: str):
    df = ds.dataset(eq_parquet_path, format="parquet").to_table().to_pandas()
    df["run_id"] = RUN_ID
    df["ingestion_time_utc"] = datetime.now(timezone.utc)

    rows = df.to_dict(orient="records")
    with engine.begin() as conn:
        for r in rows:
            conn.execute(text("""
                INSERT INTO earthquakes (event_id, mag, place, time_utc, lat, lon, depth_km, run_id, ingestion_time_utc)
                VALUES (:event_id, :mag, :place, :time_utc, :lat, :lon, :depth_km, :run_id, :ingestion_time_utc)
                ON CONFLICT (event_id) DO UPDATE SET
                  mag=EXCLUDED.mag,
                  place=EXCLUDED.place,
                  time_utc=EXCLUDED.time_utc,
                  lat=EXCLUDED.lat, lon=EXCLUDED.lon,
                  depth_km=EXCLUDED.depth_km,
                  run_id=EXCLUDED.run_id,
                  ingestion_time_utc=EXCLUDED.ingestion_time_utc
            """), r)

    # (Opcional) manter coluna geom atualizada se tiver PostGIS
    if os.getenv("USE_POSTGIS", "0") == "1":
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE earthquakes SET geom = ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography
                WHERE geom IS NULL AND lat IS NOT NULL AND lon IS NOT NULL
            """))

if __name__ == "__main__":
    # paths default com base no zip que enviaste
    eq_parquet = f"{SILVER_BASE}/earthquakes/date={RUN_DATE}/data.parquet"
    stats_parquet = f"{SILVER_BASE}/run_stats/date={RUN_DATE}/run_id={RUN_ID}/stats.parquet"
    upsert_ingestion_run(stats_parquet)
    upsert_earthquakes(eq_parquet)
    print("Upsert concluído.")
