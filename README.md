# IIoT Platform — Data & Database Foundation (Phase 1)

Customized **Industrial IoT (IIoT) monitoring platform** based on the SKF project
*"Development of a Customized IIoT Platform with AI-Powered Agent for Industrial
Data Monitoring, Analysis, and Decision Support."*

This repository currently contains **only Phase 1: the data and database
foundation.** The frontend, AI agent, RAG, Kepware/OPC UA/MQTT connectors, and
predictive-maintenance layers are intentionally **not** implemented yet.

## Purpose

Build a verified, source-agnostic industrial time-series database from a real
industrial dataset:

```
MetroPT-3 CSV
  → Dataset Inspection
  → Validation (JSON report)
  → Transformation (wide → tag-oriented)
  → PostgreSQL + TimescaleDB
  → Verified Industrial Time-Series Database
```

The schema is deliberately **tag-oriented** so that the CSV source can later be
replaced with live industrial sources (Kepware, OPC UA, PLCs, SCADA, MQTT)
**without redesigning the database** — a new source simply becomes another
machine with tags feeding the same `sensor_readings` table.

## Dataset source

**UCI MetroPT-3 (Air Compressor) dataset** — multivariate time series from the
Air Production Unit (APU) compressor of an operational metro train, logged
Feb–Aug 2020.

- Source: INESC TEC / University of Porto (Davari, Veloso, Ribeiro, Gama).
- Papers: *The MetroPT dataset for predictive maintenance*, Scientific Data 9
  (2022) 764 (DOI 10.1038/s41597-022-01877-3); DSAA 2021
  (DOI 10.1109/DSAA53316.2021.9564181).
- The dataset is **not** committed to this repo (git-ignored). Place it in
  `data/raw/` (a `.zip` or the extracted `.csv`).

### Dataset structure (verified by inspection)

- **1,516,948 rows**, 17 columns (an unnamed index column + `timestamp` + 15 signals).
- Timestamp range **2020-02-01 00:00:00 → 2020-09-01 03:59:50**.
- Dominant sampling interval **10 s** (~88% of gaps; larger gaps = logging outages).
- No missing values; all 8 digital signals take values `{0.0, 1.0}`.

**Signals (units per official documentation; digital signals have no unit):**

| Column            | Class   | Unit | Meaning |
|-------------------|---------|------|---------|
| TP2               | analog  | bar  | Pressure on the compressor |
| TP3               | analog  | bar  | Pressure at the pneumatic panel |
| H1                | analog  | bar  | Pressure drop at cyclonic separator filter discharge |
| DV_pressure       | analog  | bar  | Pressure drop when towers discharge air dryers (0 = under load) |
| Reservoirs        | analog  | bar  | Downstream reservoir pressure (≈ TP3) |
| Oil_temperature   | analog  | °C   | Compressor oil temperature |
| Motor_current     | analog  | A    | One-phase motor current (~0/4/7/9 A) |
| COMP              | digital | —    | Air intake valve signal |
| DV_eletric        | digital | —    | Outlet valve control signal |
| Towers            | digital | —    | Drying tower selector |
| MPG               | digital | —    | Load-start signal (< 8.2 bar) |
| LPS               | digital | —    | Low-pressure signal (< 7 bar) |
| Pressure_switch   | digital | —    | Air-drying tower discharge detector |
| Oil_level         | digital | —    | Oil-level signal |
| Caudal_impulses   | digital | —    | Air-flow pulse counter |

## Database architecture

PostgreSQL 16 + TimescaleDB. Three tables form a generic tag-oriented model:

```
machines (1) ──< tags (1) ──< sensor_readings  [hypertable on timestamp]
```

### Schema

**machines** — monitored assets (source-agnostic).
`id, machine_code (uniq), name, machine_type, location, description, created_at`

**tags** — one measurable signal/point on a machine.
`id, machine_id→machines, tag_name, display_name, data_type ('analog'|'digital'),
unit (nullable), description, created_at` — unique `(machine_id, tag_name)`.

**sensor_readings** — the time-series fact table (TimescaleDB hypertable).
`timestamp, machine_id→machines, tag_id→tags, value (double precision)` —
composite PK `(timestamp, machine_id, tag_id)`.

Why narrow/tag-oriented instead of mirroring the CSV columns? Any new signal or
new source is just new rows — no `ALTER TABLE`, no schema migration. This matches
how industrial historians / OPC UA tag spaces work.

**TimescaleDB specifics**
- `sensor_readings` is a hypertable partitioned on `timestamp`.
- Indexes: `(machine_id, tag_id, timestamp DESC)`, `(tag_id, timestamp DESC)`,
  `(machine_id, timestamp DESC)` plus the composite PK.
- Compression enabled (segment by `machine_id, tag_id`), policy compresses
  chunks older than 7 days — useful here because the data is static history.

## Project structure

```
backend/
  app/
    config.py            # env-driven config (no hardcoded secrets)
    dataset.py           # locate/extract the raw dataset
    tag_definitions.py   # verified signal→tag mapping (single source of truth)
    database/
      connection.py      # SQLAlchemy engine/session
      schema.py          # tables + hypertable + indexes + compression
    models/              # SQLAlchemy ORM: Machine, Tag, SensorReading
  scripts/
    inspect_dataset.py   # inspection + validation report
    ingest_metropt.py    # chunked, idempotent ingestion
    verify_db.py         # post-ingestion verification queries
  requirements.txt
data/
  raw/                   # dataset lives here (git-ignored)
  processed/             # dataset_report.json
docker-compose.yml
.env.example
.gitignore
README.md
```

## Setup

### 1. Prerequisites
- Docker + Docker Compose
- Python 3.11–3.13

### 2. Configure environment
```bash
cp .env.example .env         # adjust credentials if you like
```
Environment variables used: `DATABASE_URL`, `POSTGRES_USER`, `POSTGRES_PASSWORD`,
`POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`.

### 3. Place the dataset
Put the MetroPT-3 `.zip` or `MetroPT3(AirCompressor).csv` into `data/raw/`.
(The scripts auto-locate and, if needed, extract it.)

### 4. Start the database
```bash
docker compose up -d
docker compose ps           # wait until healthy
```

### 5. Create the Python environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

## Usage

All scripts are run from the `backend/` directory.

### Inspect & validate the dataset
```bash
cd backend
python scripts/inspect_dataset.py
```
Writes `data/processed/dataset_report.json` and prints a console summary
(rows, columns, dtypes, timestamp range, missing values, duplicates, numeric
min/max/mean, digital unique values, sampling-interval stats, invalid values).

### (Optional) Estimate the downsampling reduction first
```bash
python scripts/estimate_downsample.py            # reads the CSV only, writes nothing
```
Reports, per candidate bucket size, how many readings would result. The default
**90 s** bucket yields **~2.53M readings** (88.9% smaller than the raw 22.75M)
while keeping full Feb→Sep coverage and all 15 tags.

### Ingest into TimescaleDB
```bash
python scripts/ingest_metropt.py
```
Creates the schema/hypertable, inserts the machine and tag metadata, then streams
the CSV in chunks (wide → tag-oriented long form) with batched inserts. It is
**idempotent**: re-running resumes past already-ingested data and uses
`ON CONFLICT DO NOTHING`, so no duplicate readings are created.

**Downsampling (on by default).** To keep the Phase-1 dashboard fast, the raw
~10 s cadence is aggregated into fixed time buckets before loading
(`DOWNSAMPLE_INTERVAL`, default `90s`): analog signals use the bucket **mean**
(trend-preserving), digital signals use the bucket **majority** (0/1 state). This
is a read-only transform — the raw CSV is never modified. Buckets are computed
with a carry-over buffer so none is split across read chunks. Set
`DOWNSAMPLE_ENABLED=false` to ingest the full raw resolution instead.

### Verify the database
```bash
python scripts/verify_db.py
```
Reports counts, timestamp range, readings per tag (with min/max/avg), a
missing-data check, sample joined records, and hypertable/index status.

### Handy SQL checks
```bash
docker compose exec timescaledb psql -U iiot -d iiot_platform -c \
  "SELECT count(*) FROM sensor_readings;"

docker compose exec timescaledb psql -U iiot -d iiot_platform -c \
  "SELECT t.tag_name, count(*) FROM sensor_readings sr
   JOIN tags t ON t.id = sr.tag_id GROUP BY t.tag_name ORDER BY t.tag_name;"
```

## Running the monitoring dashboard (Phase 2)

The application layer is **TimescaleDB/PostgreSQL → FastAPI → React dashboard**.
With the database running and data ingested (above), start the two servers:

**1. Backend API** (from `backend/`):
```bash
../.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```
- Swagger UI / API docs: **http://localhost:8000/docs**
- Endpoints: `/api/health`, `/api/machines`, `/api/tags`, `/api/tags/{id}`,
  `/api/readings/latest`, `/api/readings/summary`, `/api/readings/trend`,
  `/api/readings/statistics`

**2. Frontend** (from `frontend/`):
```bash
npm install      # first time only
npm run dev
```
- Dashboard: **http://localhost:5173**

The React app talks **only** to the FastAPI API (configured via
`frontend/.env` → `VITE_API_BASE_URL`); it never connects to PostgreSQL directly.

**Architecture notes**
- Clean layering: routers → services (all SQL) → schemas; no SQL in handlers.
- Performance for the large dataset: time-range filtering + server-side
  downsampling (`date_bin`, capped at ~2000 points) so the browser never pulls
  the full history; a single `/summary` query backs the KPI cards + tag table.
- The dataset is historical (2020), so the dashboard anchors its relative time
  ranges (Last 1h/6h/24h) to the **latest available data timestamp**.
- Status is a neutral **"Monitoring"** by default — no thresholds are invented.
  Real Normal/Warning/Critical bands are configured explicitly in
  `backend/app/thresholds.py` once known (proper anomaly detection is a later phase).

## Phase 1 completion criteria

1. PostgreSQL + TimescaleDB running — `docker compose up -d`.
2. MetroPT-3 inspected & validated — `inspect_dataset.py`.
3. Validation report generated — `data/processed/dataset_report.json`.
4. Industrial tag schema created — `machines`, `tags`, `sensor_readings`.
5. Real MetroPT-3 data ingested — `ingest_metropt.py`.
6. TimescaleDB holds the time-series data (hypertable).
7. Verification queries retrieve real readings — `verify_db.py`.
8. Entire process documented & reproducible (this README).

## Explicitly out of scope for Phase 1

React, FastAPI endpoints, AI agent, RAG, LLM / LangChain / LangGraph, Kepware,
OPC UA, MQTT, predictive maintenance, anomaly detection. These come in later
phases and are designed to plug into the same database without redesign.
