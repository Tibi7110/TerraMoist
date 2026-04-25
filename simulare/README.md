# Simulare (backend only)

Acest folder contine doar logica de backend pentru simularea unui sistem ESP32 de irigatii.
Nu modifica nimic in `web/`.

## Ce contine

- `schemas.py`: contracte de date (request/response/status)
- `engine.py`: logica de calcul (volum, durata, economie apa, payload comanda)
- `service.py`: runtime in-memory pentru run-uri (start/stop/complete/list)
- `api.py`: API FastAPI standalone pentru simulare

## Rulare locala

Din radacina proiectului:

```bash
uvicorn simulare.api:app --reload --port 8010
```

## Endpoint-uri

- `GET /health`
- `POST /simulare/start`
- `GET /simulare`
- `GET /simulare/{run_id}`
- `POST /simulare/{run_id}/stop`
- `POST /simulare/{run_id}/complete`

## Exemplu request start

```json
{
  "farmer_id": "farm-001",
  "parcel_id": "parcel-14",
  "parcel_name": "Parcel 14",
  "bbox": [27.3, 44.55, 27.5, 44.7],
  "area_hectares": 12.4,
  "recommended_irrigation_mm": 18,
  "irrigation_system_type": "fixed",
  "subscription_plan": "pro"
}
```
