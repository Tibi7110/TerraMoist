"""FAO-56 style irrigation recommendation model for the smoke-test pipeline.

This is intentionally dependency-free. It estimates moisture from the rendered
NDMI PNG by mapping the known evalscript colours back to dry/wet classes, then
runs a daily water balance using Open-Meteo FAO ET0 and precipitation.
"""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    try:
        from weather_agent import WeatherForecast
    except ModuleNotFoundError:
        from scripts.weather_agent import WeatherForecast


@dataclass(frozen=True)
class MoistureFeatures:
    valid_pixel_ratio: float
    moisture_score: float
    dry_pixel_ratio: float
    initial_water_deficit_mm: float

    def to_dict(self) -> dict[str, float]:
        return {
            "valid_pixel_ratio": round(self.valid_pixel_ratio, 4),
            "moisture_score": round(self.moisture_score, 4),
            "dry_pixel_ratio": round(self.dry_pixel_ratio, 4),
            "initial_water_deficit_mm": round(self.initial_water_deficit_mm, 2),
        }


@dataclass(frozen=True)
class DailyWaterBalanceEntry:
    date: str
    previous_deficit_mm: float
    et0_mm: float
    precipitation_mm: float
    irrigation_mm: float
    deficit_mm: float

    def to_dict(self) -> dict[str, float | str]:
        return {
            "date": self.date,
            "previous_deficit_mm": round(self.previous_deficit_mm, 2),
            "et0_mm": round(self.et0_mm, 2),
            "precipitation_mm": round(self.precipitation_mm, 2),
            "irrigation_mm": round(self.irrigation_mm, 2),
            "deficit_mm": round(self.deficit_mm, 2),
        }


@dataclass(frozen=True)
class WaterBalance:
    initial_deficit_mm: float
    final_deficit_mm: float
    irrigation_threshold_mm: float
    max_deficit_mm: float
    daily: tuple[DailyWaterBalanceEntry, ...]

    def to_dict(self) -> dict:
        return {
            "formula": "Water Deficit(t) = Water Deficit(t-1) + ET0 - Precipitation - Irrigation",
            "initial_deficit_mm": round(self.initial_deficit_mm, 2),
            "final_deficit_mm": round(self.final_deficit_mm, 2),
            "irrigation_threshold_mm": round(self.irrigation_threshold_mm, 2),
            "max_deficit_mm": round(self.max_deficit_mm, 2),
            "daily": [entry.to_dict() for entry in self.daily],
        }


@dataclass(frozen=True)
class IrrigationRecommendation:
    should_irrigate: bool
    label: str
    reason: str
    recommended_irrigation_mm: float
    moisture: MoistureFeatures
    water_balance: WaterBalance
    weather: "WeatherForecast"

    def to_dict(self) -> dict:
        return {
            "should_irrigate": self.should_irrigate,
            "label": self.label,
            "reason": self.reason,
            "recommended_irrigation_mm": round(self.recommended_irrigation_mm, 2),
            "moisture": self.moisture.to_dict(),
            "water_balance": self.water_balance.to_dict(),
            "weather": self.weather.to_dict(),
        }


class IrrigationModel:
    """FAO-56 daily water balance model.

    The smoke test does not yet know crop type, root depth, soil texture, or
    field capacity. Until those exist, NDMI initializes a bounded deficit
    estimate and FAO ET0/precipitation drive the daily calculation.
    """

    max_deficit_mm = 60.0
    irrigation_threshold_mm = 35.0

    # RGB values produced by NDMI_EVALSCRIPT, with a dry->wet score.
    _NDMI_PALETTE: tuple[tuple[tuple[int, int, int], float], ...] = (
        ((140, 69, 18), 0.05),   # very dry
        ((217, 166, 33), 0.25),  # dry
        ((242, 230, 77), 0.45),  # moderate
        ((102, 191, 77), 0.65),  # moist
        ((26, 140, 64), 0.82),   # wet
        ((26, 89, 179), 1.00),   # very wet
    )

    def recommend(
        self,
        *,
        ndmi_png: bytes,
        weather: "WeatherForecast",
        irrigation_by_day_mm: tuple[float, ...] | None = None,
    ) -> IrrigationRecommendation:
        moisture = self.extract_moisture_features(ndmi_png)
        water_balance = self.calculate_daily_water_balance(
            weather=weather,
            initial_deficit_mm=moisture.initial_water_deficit_mm,
            irrigation_by_day_mm=irrigation_by_day_mm,
        )
        should_irrigate = (
            water_balance.final_deficit_mm >= water_balance.irrigation_threshold_mm
        )
        label = "irrigate" if should_irrigate else "hold"
        recommended_irrigation_mm = (
            water_balance.final_deficit_mm
            if should_irrigate
            else 0.0
        )

        if should_irrigate:
            reason = (
                "FAO-56 water balance projects the field above the allowed "
                "deficit threshold."
            )
        else:
            reason = "FAO-56 water balance stays below the irrigation threshold."

        return IrrigationRecommendation(
            should_irrigate=should_irrigate,
            label=label,
            reason=reason,
            recommended_irrigation_mm=recommended_irrigation_mm,
            moisture=moisture,
            water_balance=water_balance,
            weather=weather,
        )

    def calculate_daily_water_balance(
        self,
        *,
        weather: "WeatherForecast",
        initial_deficit_mm: float,
        irrigation_by_day_mm: tuple[float, ...] | None = None,
    ) -> WaterBalance:
        irrigation = irrigation_by_day_mm or tuple(0.0 for _ in weather.daily_dates)
        daily: list[DailyWaterBalanceEntry] = []
        deficit = initial_deficit_mm

        for idx, date in enumerate(weather.daily_dates):
            previous = deficit
            et0 = weather.daily_et0_mm[idx]
            precipitation = weather.daily_precipitation_mm[idx]
            irrigation_mm = irrigation[idx] if idx < len(irrigation) else 0.0
            deficit = _clamp(
                previous + et0 - precipitation - irrigation_mm,
                lower=0.0,
                upper=self.max_deficit_mm,
            )
            daily.append(
                DailyWaterBalanceEntry(
                    date=date,
                    previous_deficit_mm=previous,
                    et0_mm=et0,
                    precipitation_mm=precipitation,
                    irrigation_mm=irrigation_mm,
                    deficit_mm=deficit,
                )
            )

        return WaterBalance(
            initial_deficit_mm=initial_deficit_mm,
            final_deficit_mm=deficit,
            irrigation_threshold_mm=self.irrigation_threshold_mm,
            max_deficit_mm=self.max_deficit_mm,
            daily=tuple(daily),
        )

    def extract_moisture_features(self, png_bytes: bytes) -> MoistureFeatures:
        width, height, pixels = _decode_png_rgba(png_bytes)
        total = width * height
        valid = 0
        dry = 0
        score_sum = 0.0

        for red, green, blue, alpha in pixels:
            if alpha == 0:
                continue
            score = self._nearest_ndmi_score(red, green, blue)
            valid += 1
            score_sum += score
            if score <= 0.25:
                dry += 1

        if valid == 0:
            return MoistureFeatures(
                valid_pixel_ratio=0.0,
                moisture_score=0.0,
                dry_pixel_ratio=0.0,
                initial_water_deficit_mm=self.max_deficit_mm,
            )

        moisture_score = score_sum / valid
        return MoistureFeatures(
            valid_pixel_ratio=valid / total,
            moisture_score=moisture_score,
            dry_pixel_ratio=dry / valid,
            initial_water_deficit_mm=(1.0 - moisture_score) * self.max_deficit_mm,
        )

    def _nearest_ndmi_score(self, red: int, green: int, blue: int) -> float:
        _, score = min(
            self._NDMI_PALETTE,
            key=lambda item: (
                (red - item[0][0]) ** 2
                + (green - item[0][1]) ** 2
                + (blue - item[0][2]) ** 2
            ),
        )
        return score


def _decode_png_rgba(data: bytes) -> tuple[int, int, list[tuple[int, int, int, int]]]:
    """Decode non-interlaced 8-bit RGB/RGBA PNGs produced by Sentinel Hub."""
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Expected PNG bytes")

    offset = 8
    width = height = bit_depth = color_type = interlace = None
    compressed = bytearray()

    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = data[offset + 4:offset + 8]
        chunk_data = data[offset + 8:offset + 8 + length]
        offset += 12 + length

        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _, _, interlace = struct.unpack(
                ">IIBBBBB",
                chunk_data,
            )
        elif chunk_type == b"IDAT":
            compressed.extend(chunk_data)
        elif chunk_type == b"IEND":
            break

    if width is None or height is None:
        raise ValueError("PNG is missing IHDR")
    if bit_depth != 8 or color_type not in (2, 6) or interlace != 0:
        raise ValueError("Only non-interlaced 8-bit RGB/RGBA PNGs are supported")

    channels = 4 if color_type == 6 else 3
    row_size = width * channels
    raw = zlib.decompress(bytes(compressed))
    rows: list[bytes] = []
    cursor = 0
    previous = bytes(row_size)

    for _ in range(height):
        filter_type = raw[cursor]
        cursor += 1
        row = bytearray(raw[cursor:cursor + row_size])
        cursor += row_size
        _unfilter_row(row, previous, filter_type, channels)
        rows.append(bytes(row))
        previous = bytes(row)

    pixels: list[tuple[int, int, int, int]] = []
    for row in rows:
        for idx in range(0, len(row), channels):
            red, green, blue = row[idx], row[idx + 1], row[idx + 2]
            alpha = row[idx + 3] if channels == 4 else 255
            pixels.append((red, green, blue, alpha))

    return width, height, pixels


def _unfilter_row(
    row: bytearray,
    previous: bytes,
    filter_type: int,
    bytes_per_pixel: int,
) -> None:
    for idx in range(len(row)):
        left = row[idx - bytes_per_pixel] if idx >= bytes_per_pixel else 0
        up = previous[idx]
        up_left = previous[idx - bytes_per_pixel] if idx >= bytes_per_pixel else 0

        if filter_type == 0:
            prediction = 0
        elif filter_type == 1:
            prediction = left
        elif filter_type == 2:
            prediction = up
        elif filter_type == 3:
            prediction = (left + up) // 2
        elif filter_type == 4:
            prediction = _paeth(left, up, up_left)
        else:
            raise ValueError(f"Unsupported PNG filter type: {filter_type}")

        row[idx] = (row[idx] + prediction) & 0xFF


def _paeth(left: int, up: int, up_left: int) -> int:
    estimate = left + up - up_left
    dist_left = abs(estimate - left)
    dist_up = abs(estimate - up)
    dist_up_left = abs(estimate - up_left)
    if dist_left <= dist_up and dist_left <= dist_up_left:
        return left
    if dist_up <= dist_up_left:
        return up
    return up_left


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))
