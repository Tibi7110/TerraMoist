**Two paths to satellite data:**
1. **Frontend → CDSE WMS direct** — for interactive map tiles. Public, scalable, cached by Sentinel Hub.
2. **Backend → CDSE Process API** — for on-demand renders, time-series statistics, and operations that require server-side credentials.

---

## ✨ Features (current)

- 🌍 **Global interactive map** — zoom from planetary view to individual fields
- 🎚️ **Layer switcher** — NDMI, SAR moisture, true color, NDVI
- 📅 **Date picker** with intelligent ±10-day mosaicking window for cloud-free composites
- 📍 **Preset regions** for fast demos: Bărăgan, Dobrogea, Romania, Europe
- 🎨 **Color-coded legend** — intuitive dry → wet ramp (brown → blue)
- 🛰️ **End-to-end EU stack** — every byte flows through Copernicus

## 🚧 In progress

- ✏️ **Field drawing tool** — farmers define their own AOI by clicking polygon vertices on the map
- 📊 **Time-series chart** — NDMI evolution per field over the last 6 months
- 💧 **Irrigation recommendations** — automated alerts when fields cross a moisture threshold
- 🔬 **Ground-truth validation** — cross-check against ISMN / SMAP reference sites

---

## 🔧 Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, react-leaflet, Leaflet |
| Backend | Python 3.11+, FastAPI, httpx (async), Pydantic v2 |
| Data | Sentinel-1 GRD, Sentinel-2 L2A via Copernicus Data Space Ecosystem |
| Auth | OAuth2 client_credentials with token caching & 60s refresh buffer |
| Indices | Custom JavaScript evalscripts running inside Sentinel Hub |
| Deploy | (Local dev for hackathon — Vercel/Railway compatible) |

---

## 🚀 Run locally

### Prerequisites

- Python 3.11+
- Node.js 18+
- A free [Copernicus Data Space Ecosystem](https://dataspace.copernicus.eu) account
- An OAuth client created in the [Sentinel Hub Dashboard](https://shapps.dataspace.copernicus.eu/dashboard) (User Settings → OAuth clients → Client Credentials flow)
- A Sentinel Hub WMS Configuration with three layers: `MOISTURE_INDEX`, `SAR_MOISTURE`, `TRUE_COLOR`

### 1. Backend

```bash
cd terramoist  # or wherever you cloned this
python -m venv .venv
source .venv/Scripts/activate    # Windows Git Bash
# or:  source .venv/bin/activate  # macOS / Linux

pip install -r requirements.txt
cp .env.example .env
# edit .env: paste your CDSE_CLIENT_ID and CDSE_CLIENT_SECRET

uvicorn app.main:app --reload
```

Verify: open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Smoke test (in a second terminal):

```bash
source .venv/Scripts/activate
python scripts/smoke_test.py
# → should save ndmi_baragan.png with a Bărăgan soil-moisture render
```

### 2. Frontend

```bash
cd frontend
npm install

# Edit src/config.js and paste YOUR Sentinel Hub Configuration Instance ID
# (the UUID from the Configuration Utility → terramoist-public)

npm run dev
```

Open [http://localhost:5173](http://localhost:5173) and click **🌾 Bărăgan** to see live tiles.

---

## 📁 Project structure