"""Baseline irrigation recommendation model for the smoke-test pipeline.

This is intentionally dependency-free. It estimates moisture from the rendered
NDMI PNG by mapping the known evalscript colours back to dry/wet classes, then
combines that signal with weather forecast pressure.
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

    def to_dict(self) -> dict[str, float]:
        return {
            "valid_pixel_ratio": round(self.valid_pixel_ratio, 4),
            "moisture_score": round(self.moisture_score, 4),
            "dry_pixel_ratio": round(self.dry_pixel_ratio, 4),
        }


@dataclass(frozen=True)
class IrrigationRecommendation:
    should_irrigate: bool
    irrigation_need_score: float
    label: str
    reason: str
    moisture: MoistureFeatures
    weather: "WeatherForecast"

    def to_dict(self) -> dict:
        return {
            "should_irrigate": self.should_irrigate,
            "irrigation_need_score": round(self.irrigation_need_score, 4),
            "label": self.label,
            "reason": self.reason,
            "moisture": self.moisture.to_dict(),
            "weather": self.weather.to_dict(),
        }


class IrrigationModel:
    """Small baseline model that can later be replaced with trained weights."""

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
    ) -> IrrigationRecommendation:
        moisture = self.extract_moisture_features(ndmi_png)
        drying_deficit_mm = max(0.0, -weather.water_balance_next_7d_mm)
        weather_pressure = _clamp(drying_deficit_mm / 30.0)
        heat_pressure = _clamp((weather.avg_max_temp_next_7d_c - 28.0) / 10.0)
        satellite_stress = 1.0 - moisture.moisture_score

        score = (
            0.60 * satellite_stress
            + 0.30 * weather_pressure
            + 0.10 * heat_pressure
        )
        score = _clamp(score)

        enough_rain_soon = weather.precipitation_next_3d_mm >= 8.0
        should_irrigate = score >= 0.55 and not enough_rain_soon
        label = "irrigate" if should_irrigate else "hold"

        if enough_rain_soon:
            reason = "Rain forecast in the next 3 days is high enough to delay irrigation."
        elif should_irrigate:
            reason = "NDMI indicates moisture stress and the 7-day forecast has drying pressure."
        else:
            reason = "Current moisture and forecast do not cross the irrigation threshold."

        return IrrigationRecommendation(
            should_irrigate=should_irrigate,
            irrigation_need_score=score,
            label=label,
            reason=reason,
            moisture=moisture,
            weather=weather,
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
            )

        return MoistureFeatures(
            valid_pixel_ratio=valid / total,
            moisture_score=score_sum / valid,
            dry_pixel_ratio=dry / valid,
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
