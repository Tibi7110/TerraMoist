# TerraMoist Backend

FastAPI service that serves soil-moisture tiles on top of the **Copernicus Data Space Ecosystem (CDSE)**.

## Stack

- **FastAPI** — async HTTP framework
- **httpx** — async client for CDSE OAuth + Sentinel Hub Process API
- **Pydantic v2** — request/response validation
- **CDSE Sentinel Hub Process API** — on-the-fly raster generation using custom evalscripts

No third-party re-hosters (no GEE). End-to-end EU stack.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET  | `/api/v1/health`  | Liveness + config check |
| GET  | `/api/v1/regions` | List preset demo regions (Bărăgan, Dobrogea) |
| POST | `/api/v1/tiles`   | Returns a PNG for `{index, bbox, date_from, date_to}` |

Supported indices: `ndmi` (Sentinel-2), `sar_moisture` (Sentinel-1 VV), `true_color` (Sentinel-2).

## Setup

### 1. Get CDSE OAuth credentials

1. Log in at https://dataspace.copernicus.eu
2. Hover the profile icon (top right) → click **Sentinel Hub** to open the Sentinel Hub dashboard
3. Go to **User Settings** → **OAuth clients** → **Create**
4. Name: `terramoist-backend`, Supported flow: **Client Credentials**
5. Copy `client_id` and `client_secret` — the secret is shown ONCE

### 2. Install

```bash
cd terramoist-backend
python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash
pip install -r requirements.txt
cp .env.example .env
# edit .env → paste CDSE_CLIENT_ID and CDSE_CLIENT_SECRET
```

### 3. Run

```bash
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for interactive Swagger UI.

### 4. Smoke test

In a second terminal (keep uvicorn running):

```bash
source .venv/Scripts/activate
python scripts/smoke_test.py
```

If configured, `ndmi_baragan.png` appears in the working directory.# TerraMoist
# TerraMoist
