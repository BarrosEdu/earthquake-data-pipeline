

.
├─ ingest/
│  ├─ fetch_data.py          # baixa dados da API pública (ex: USGS)
│  ├─ transform.py           # normaliza e converte para Parquet
│  └─ load_postgres.py       # insere/atualiza no banco
│
├─ api/
│  ├─ main.py                # app FastAPI principal
│  ├─ routers/
│  │   └─ earthquakes.py     # endpoints /earthquakes
│  └─ db.py                  # conexão e schema SQLAlchemy
│
├─ dashboard/
│  └─ app.py                 # Streamlit dashboard com mapa e filtros
│
├─ data/
│  ├─ bronze/                # JSONs brutos (raw)
│  └─ silver/                # Parquet normalizado
│
├─ schemas/
│  └─ models.py              # Pydantic models (validação)
│
├─ scripts/
│  └─ init_db.sql            # criação das tabelas no Postgres
│
├─ .env                      # de ambiente (DB_URL etc.)
└─ README.md                 # instruções, suposições, limitações
