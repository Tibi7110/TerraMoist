"""Weather forecast client for irrigation recommendations."""
from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

import httpx


OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


@dataclass(frozen=True)
class WeatherForecast:
    latitude: float
    longitude: float
    daily_dates: tuple[str, ...]
    daily_precipitation_mm: tuple[float, ...]
    daily_et0_mm: tuple[float, ...]
    daily_max_temp_c: tuple[float, ...]

    @property
    def precipitation_next_7d_mm(self) -> float:
        return sum(self.daily_precipitation_mm[:7])

    @property
    def evapotranspiration_next_7d_mm(self) -> float:
        return sum(self.daily_et0_mm[:7])

    @property
    def water_balance_next_7d_mm(self) -> float:
        return self.precipitation_next_7d_mm - self.evapotranspiration_next_7d_mm

    @property
    def avg_max_temp_next_7d_c(self) -> float:
        return mean(self.daily_max_temp_c[:7])

    def to_response(self) -> dict:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "forecast_days": len(self.daily_dates),
            "daily": [
                {
                    "date": date,
                    "precipitation_mm": round(precipitation, 2),
                    "et0_fao_mm": round(et0, 2),
                    "max_temp_c": round(max_temp, 2),
                }
                for date, precipitation, et0, max_temp in zip(
                    self.daily_dates,
                    self.daily_precipitation_mm,
                    self.daily_et0_mm,
                    self.daily_max_temp_c,
                )
            ],
            "precipitation_next_7d_mm": round(self.precipitation_next_7d_mm, 2),
            "evapotranspiration_next_7d_mm": round(
                self.evapotranspiration_next_7d_mm,
                2,
            ),
            "water_balance_next_7d_mm": round(self.water_balance_next_7d_mm, 2),
        }


class WeatherClient:
    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str = OPEN_METEO_FORECAST_URL,
    ) -> None:
        self._client = client
        self._base_url = base_url

    async def forecast_for_bbox(
        self,
        bbox: tuple[float, float, float, float],
        *,
        forecast_days: int = 7,
    ) -> WeatherForecast:
        min_lon, min_lat, max_lon, max_lat = bbox
        latitude = (min_lat + max_lat) / 2
        longitude = (min_lon + max_lon) / 2
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
        response = await self._client.get(self._base_url, params=params, timeout=20)
        response.raise_for_status()
        daily = response.json()["daily"]

        return WeatherForecast(
            latitude=latitude,
            longitude=longitude,
            daily_dates=tuple(str(x) for x in daily["time"][:forecast_days]),
            daily_precipitation_mm=tuple(
                float(x or 0) for x in daily["precipitation_sum"][:forecast_days]
            ),
            daily_et0_mm=tuple(
                float(x or 0)
                for x in daily["et0_fao_evapotranspiration"][:forecast_days]
            ),
            daily_max_temp_c=tuple(
                float(x or 0) for x in daily["temperature_2m_max"][:forecast_days]
            ),
        )
