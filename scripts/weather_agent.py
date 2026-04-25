"""Weather forecast agent used by the irrigation smoke test.

The default provider is Open-Meteo because it does not require an API key for
basic forecast calls. The agent returns a compact feature set that the local
irrigation model can consume.
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

import httpx


OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


@dataclass(frozen=True)
class WeatherForecast:
    """Weather features for the centre point of a requested region."""

    latitude: float
    longitude: float
    forecast_days: int
    precipitation_next_3d_mm: float
    precipitation_next_7d_mm: float
    evapotranspiration_next_7d_mm: float
    avg_max_temp_next_7d_c: float
    max_temp_next_7d_c: float

    @property
    def water_balance_next_7d_mm(self) -> float:
        """Positive means rain exceeds ET0, negative means drying pressure."""
        return self.precipitation_next_7d_mm - self.evapotranspiration_next_7d_mm

    def to_dict(self) -> dict[str, float | int]:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "forecast_days": self.forecast_days,
            "precipitation_next_3d_mm": round(self.precipitation_next_3d_mm, 2),
            "precipitation_next_7d_mm": round(self.precipitation_next_7d_mm, 2),
            "evapotranspiration_next_7d_mm": round(
                self.evapotranspiration_next_7d_mm, 2
            ),
            "avg_max_temp_next_7d_c": round(self.avg_max_temp_next_7d_c, 2),
            "max_temp_next_7d_c": round(self.max_temp_next_7d_c, 2),
            "water_balance_next_7d_mm": round(self.water_balance_next_7d_mm, 2),
        }


class WeatherAgent:
    """Fetches weather features for a bbox centre point."""

    def __init__(
        self,
        *,
        base_url: str = OPEN_METEO_FORECAST_URL,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url
        self._client = client or httpx.Client(timeout=20)

    def forecast_for_bbox(
        self,
        bbox: tuple[float, float, float, float],
        *,
        forecast_days: int = 7,
    ) -> WeatherForecast:
        min_lon, min_lat, max_lon, max_lat = bbox
        latitude = (min_lat + max_lat) / 2
        longitude = (min_lon + max_lon) / 2
        return self.forecast_for_point(
            latitude,
            longitude,
            forecast_days=forecast_days,
        )

    def forecast_for_point(
        self,
        latitude: float,
        longitude: float,
        *,
        forecast_days: int = 7,
    ) -> WeatherForecast:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "forecast_days": forecast_days,
            "timezone": "auto",
            "daily": ",".join(
                [
                    "precipitation_sum",
                    "et0_fao_evapotranspiration",
                    "temperature_2m_max",
                ]
            ),
        }
        response = self._client.get(self._base_url, params=params)
        response.raise_for_status()
        daily = response.json()["daily"]

        precipitation = [float(x or 0) for x in daily["precipitation_sum"]]
        evapotranspiration = [
            float(x or 0) for x in daily["et0_fao_evapotranspiration"]
        ]
        max_temps = [float(x or 0) for x in daily["temperature_2m_max"]]

        return WeatherForecast(
            latitude=latitude,
            longitude=longitude,
            forecast_days=forecast_days,
            precipitation_next_3d_mm=sum(precipitation[:3]),
            precipitation_next_7d_mm=sum(precipitation[:7]),
            evapotranspiration_next_7d_mm=sum(evapotranspiration[:7]),
            avg_max_temp_next_7d_c=mean(max_temps[:7]),
            max_temp_next_7d_c=max(max_temps[:7]),
        )
