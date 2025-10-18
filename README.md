# earthquake-data-pipeline

> **Data Engineering**  
> Real-time(ish) earthquake ingestion → transform → Postgres/PostGIS storage → API + optional dashboard.

- [Earthquake Monitor - Dashboard](https://earthquake-data-pipeline.streamlit.app)
- [API Docs](https://earthquake-ce5c9a0f9ec7.herokuapp.com/docs)
> **Note:**  
> This API uses a lightweight API Key middleware for demonstration.  
> You can use the demo key below to test the endpoints directly:  
> 
> ```
> x-api-key: demo-4e3f5a97-0b2a-4d92-b6c4-71a5e4181d43
> ```
> 

## 1. Overview

This repository implements a simplified real-time data pipeline for global earthquake monitoring:

- **Ingest** earthquake events from a public source (**USGS Earthquake API**).
- **Transform** into a structured schema (magnitude, time, depth, coordinates, etc.).
- **Store** events in **PostgreSQL + PostGIS** (with a spatial index for geo queries).
- **Serve** results via a **FastAPI** microservice with filters for recency, magnitude and proximity.
- **Governance** using a lightweight **RUN_ID** audit trail and timestamps.

![Architecture Diagram](architecture_diagram.svg)

> The pipeline also keeps a Parquet **silver** layer for quick ad‑hoc analytics and replayability.

## 2. Tech Stack

- **Python** (3.11+), **FastAPI**, **Pydantic**, **Requests**
- **Pandas** / **PyArrow**
- **PostgreSQL 14+** with **PostGIS**
- **SQLAlchemy** (if present) for DB integration
- **Streamlit** (optional dashboard)

## 3. Repository Structure
```
.
├── ingest/
│ ├── fetch_data.py # Fetches raw data from USGS API (bronze layer)
│ ├── transform.py # Cleans and normalizes to Parquet (silver layer)
│ └── load_postgres.py # Loads normalized data into PostgreSQL
│
├── api/
│ ├── main.py # FastAPI app entrypoint
│ ├── routers/
│ │ └── earthquakes.py # REST endpoints for querying earthquakes
│ ├── db.py # SQLAlchemy/PostGIS connection setup
│ └── middleware/
│ └── auth.py # API Key authentication middleware
│
├── dashboard/
│ └── app.py # Streamlit visualization
│
├── schemas/
│ └── models.py # Pydantic models for validation
│
├── data/
│ ├── bronze/ # Raw JSON files (downloaded data)
│ └── silver/ # Parquet files (transformed data)
│
├── Procfile # Heroku deployment commands
├── requirements.txt # Python dependencies
├── README.md # Project documentation
└── .gitignore # Excluded files for version control
```

## 4. Setup & Run

### 4.1 Prerequisites
- Python 3.11+
- PostgreSQL 14+ with PostGIS extension
- `pip` for dependencies

### 4.2 Environment Variables
Create a `.env` (or export variables) similar to:

```
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/earthquakes
SILVER_BASE=./data/silver
USE_POSTGIS=1
```

> `RUN_ID` is a unique identifier (e.g., UTC timestamp) used for auditability per ingestion run.

### 4.3 Database Initialization (Postgres + PostGIS)

Run the following once:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;

-- earthquakes table (operational store)
CREATE TABLE IF NOT EXISTS earthquakes (
  id TEXT PRIMARY KEY,            -- source id (e.g., USGS event id)
  mag DOUBLE PRECISION,
  place TEXT,
  time_utc TIMESTAMPTZ,
  lat DOUBLE PRECISION,
  lon DOUBLE PRECISION,
  depth_km DOUBLE PRECISION,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  run_id TEXT,                    -- audit: which run loaded/updated this row
  geom GEOGRAPHY(Point, 4326)
);

-- Optional: ingestion runs audit
CREATE TABLE IF NOT EXISTS run_stats (
  run_id TEXT PRIMARY KEY,
  source TEXT,
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  rows_ingested BIGINT,
  notes TEXT
);

-- Spatial index
CREATE INDEX IF NOT EXISTS idx_eq_geom ON earthquakes USING GIST (geom);
```

If your table already exists but `geom` is null, run:

```sql
UPDATE earthquakes
SET geom = ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography
WHERE geom IS NULL AND lat IS NOT NULL AND lon IS NOT NULL;
```

### 4.4 Install & Run

```bash
# Install deps
pip install -r requirements.txt

# 1) Ingest + Transform
python ingest/fetch_data.py
python ingest/transform.py

# 2) Load into Postgres
python ingest/load_postgres.py

# 3) Start API
uvicorn api.main:app --reload --port 8000

# 4) (Optional) Dashboard
streamlit run dashboard/app.py
```

## 5. API Docs - Implemented

Base URL: `https://earthquake-ce5c9a0f9ec7.herokuapp.com/docs`

### 5.1 `GET /earthquakes/recent`
Return recent earthquakes filtered by time and magnitude.

**Query params** (all optional):
- `hours` (int, default: 24)
- `min_mag` (float, default: 0.0)
- `limit` (int, default: 100; max 500)

**Example:**
```
/earthquakes/recent?hours=12&min_mag=3.5&limit=50
```

### 5.2 `GET /earthquakes/around`
Return earthquakes near a **lat/lon** within a given radius using PostGIS.

**Query params**:
- `lat` (float) – required
- `lon` (float) – required
- `radius_km` (float, default: 200)
- `hours` (int, default: 24)
- `min_mag` (float, default: 0.0)
- `limit` (int, default: 100)

**Example:**
```
/earthquakes/around?lat=34.05&lon=-118.25&radius_km=300&min_mag=2.5
```

> Implementation note: the query uses `ST_DWithin(geom, ST_MakePoint(lon,lat)::geography, radius_meters)`
> combined with time and magnitude filters.

## 6. Data Governance & Audit

- **RUN_ID** is stamped on each batch ingestion to trace provenance.
- `run_stats` table records runs with timing and counts.
- Each event row has `updated_at` timestamp for lightweight change tracking.
- Parquet silver layer maintains a reproducible snapshot of transformed events per run/date.

## 7. Performance Notes

- **Spatial index** on `geom` accelerates proximity queries.
- Parquet **columnar** storage helps quick filters in exploration/ML notebooks.
- For higher throughput, schedule ingestion frequently and use incremental upserts (by `id`).

## 8. Assumptions & Limitations

- The MVP assumes a single upstream (USGS). Multi-source merge and deduping are out of scope.
- Real-time constraints are **near real-time** (scheduled pulls, not a long-lived websocket).
- Security is basic (.env, no auth on API by default). For production, add OAuth/API keys + TLS.
- Error handling/retries are minimal by design for speed of delivery.

## 9. Design Diagram (Mermaid)

```mermaid
flowchart LR
  A[USGS Earthquake API] --> B[Ingest<br/>fetch_data.py]
  B --> C[Transform<br/>transform.py]
  C --> D[(Parquet Silver)]
  C --> E[(PostgreSQL + PostGIS)]
  E --> F[FastAPI Service<br/>/earthquakes/*]
  E --> G[Streamlit Dashboard]
  subgraph Governance
    H[RUN_ID audit & run_stats]
  end
  B --> H
  C --> H
  E --> H
```

## 10. Limitations & Known Challenges
- Latency – Data updates follow USGS feed cadence (hourly).
- No streaming (yet) – Ingestion runs in batches; WebSocket/Kafka integration out of scope for MVP.
- No historical backfill – Only current “All Day” data retained (by design).
- Single source – USGS only; multi-source federation left as future enhancement.
- Basic security – API key suitable for demo, not production-grade authentication.

## 11. Future Enhancements
- Expand to multiple data sources (EMSC, GFZ).
- Add Airflow or Prefect for orchestration.
- Add alerting for magnitude > 6.0 events.

---

**Authoring note:** Code was intentionally kept as‑is per instructions; this README and the diagram are focused on clarity and evaluability.
