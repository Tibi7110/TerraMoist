"""Irrigation recommendation engine with FAO-56 baseline and local ML history."""
from __future__ import annotations

import json
import math
import sqlite3
import struct
import zlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.services.weather import WeatherForecast


PLANT_COEFFICIENTS = {
    "none": 1.0,
    "wheat": 1.15,
    "corn": 1.2,
    "sunflower": 1.0,
    "rapeseed": 1.05,
    "soybean": 1.05,
    "vegetables": 1.1,
    "other": 1.0,
}


IRRIGATION_TYPE_EFFICIENCY = {
    "fixed": 0.9,
    "moving": 0.75,
}


@dataclass(frozen=True)
class MoistureFeatures:
    valid_pixel_ratio: float
    moisture_score: float
    dry_pixel_ratio: float
    initial_water_deficit_mm: float

    def to_response(self) -> dict:
        return {
            "valid_pixel_ratio": round(self.valid_pixel_ratio, 4),
            "moisture_score": round(self.moisture_score, 4),
            "dry_pixel_ratio": round(self.dry_pixel_ratio, 4),
            "initial_water_deficit_mm": round(self.initial_water_deficit_mm, 2),
        }


@dataclass(frozen=True)
class WaterBalance:
    initial_deficit_mm: float
    final_deficit_mm: float
    irrigation_threshold_mm: float
    max_deficit_mm: float
    daily: tuple[dict, ...]

    def to_response(self) -> dict:
        return {
            "formula": (
                "Water Deficit(t) = Water Deficit(t-1) + ETc - "
                "Precipitation - Irrigation; ETc = ET0 * Kc"
            ),
            "initial_deficit_mm": round(self.initial_deficit_mm, 2),
            "final_deficit_mm": round(self.final_deficit_mm, 2),
            "irrigation_threshold_mm": round(self.irrigation_threshold_mm, 2),
            "max_deficit_mm": round(self.max_deficit_mm, 2),
            "daily": [
                {
                    "date": entry["date"],
                    "previous_deficit_mm": round(entry["previous_deficit_mm"], 2),
                    "et0_mm": round(entry["et0_mm"], 2),
                    "precipitation_mm": round(entry["precipitation_mm"], 2),
                    "irrigation_mm": round(entry["irrigation_mm"], 2),
                    "deficit_mm": round(entry["deficit_mm"], 2),
                }
                for entry in self.daily
            ],
        }


class IrrigationHistoryStore:
    """Stores recommendation samples used by the lightweight ML model."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def add_sample(self, sample: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO irrigation_samples (
                    field_id, field_name, plant_type, bbox_json, features_json,
                    label_should_irrigate, label_irrigation_mm, source,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sample["field_id"],
                    sample["field_name"],
                    sample["plant_type"],
                    json.dumps(sample["bbox"]),
                    json.dumps(sample["features"]),
                    int(sample["label_should_irrigate"]),
                    float(sample["label_irrigation_mm"]),
                    sample["source"],
                    datetime.now(UTC).isoformat(),
                ),
            )
            conn.commit()

    def load_samples(self, limit: int = 500) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT field_id, plant_type, features_json, label_should_irrigate,
                       label_irrigation_mm
                FROM irrigation_samples
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        samples = []
        for row in rows:
            samples.append(
                {
                    "field_id": row["field_id"],
                    "plant_type": row["plant_type"],
                    "features": json.loads(row["features_json"]),
                    "label_should_irrigate": bool(row["label_should_irrigate"]),
                    "label_irrigation_mm": float(row["label_irrigation_mm"]),
                }
            )
        return samples

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS irrigation_samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    field_id TEXT NOT NULL,
                    field_name TEXT NOT NULL,
                    plant_type TEXT NOT NULL,
                    bbox_json TEXT NOT NULL,
                    features_json TEXT NOT NULL,
                    label_should_irrigate INTEGER NOT NULL,
                    label_irrigation_mm REAL NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()


class IrrigationEngine:
    max_deficit_mm = 60.0
    irrigation_threshold_mm = 35.0
    min_ml_samples = 8

    _NDMI_PALETTE: tuple[tuple[tuple[int, int, int], float], ...] = (
        ((140, 69, 18), 0.05),
        ((217, 166, 33), 0.25),
        ((242, 230, 77), 0.45),
        ((102, 191, 77), 0.65),
        ((26, 140, 64), 0.82),
        ((26, 89, 179), 1.00),
    )

    def __init__(self, store: IrrigationHistoryStore) -> None:
        self._store = store

    def recommend(
        self,
        *,
        field_id: str,
        field_name: str,
        plant_type: str,
        bbox: tuple[float, float, float, float],
        ndmi_png: bytes,
        weather: WeatherForecast,
        irrigation_events: list[dict],
        irrigation_type: str = "fixed",
    ) -> dict:
        plant_type = plant_type if plant_type in PLANT_COEFFICIENTS else "other"
        irrigation_type = (
            irrigation_type
            if irrigation_type in IRRIGATION_TYPE_EFFICIENCY
            else "fixed"
        )
        kc = PLANT_COEFFICIENTS[plant_type]
        delivery_efficiency = IRRIGATION_TYPE_EFFICIENCY[irrigation_type]
        moisture = self.extract_moisture_features(ndmi_png)
        water_balance = self.calculate_water_balance(
            weather=weather,
            initial_deficit_mm=moisture.initial_water_deficit_mm,
            crop_coefficient=kc,
            irrigation_by_day_mm=tuple(
                applied_mm * delivery_efficiency
                for applied_mm in _irrigation_by_forecast_day(
                    weather.daily_dates,
                    irrigation_events,
                )
            ),
        )
        features = self._build_features(
            moisture=moisture,
            weather=weather,
            water_balance=water_balance,
            crop_coefficient=kc,
        )
        baseline = self._baseline_prediction(water_balance)
        samples = self._store.load_samples()
        ml_prediction = self._predict_with_knn(features, samples)
        prediction = ml_prediction or baseline
        scenarios = self._build_irrigation_scenarios(
            moisture=moisture,
            water_balance=water_balance,
            irrigation_type=irrigation_type,
        )

        self._store.add_sample(
            {
                "field_id": field_id,
                "field_name": field_name,
                "plant_type": plant_type,
                "bbox": bbox,
                "features": features,
                "label_should_irrigate": baseline["should_irrigate"],
                "label_irrigation_mm": baseline["recommended_irrigation_mm"],
                "source": "fao56_pseudo_label",
            }
        )

        return {
            **prediction,
            "reason": self._reason(prediction, water_balance, ml_prediction is None),
            "bbox": bbox,
            "plant_type": plant_type,
            "irrigation_type": irrigation_type,
            "training_samples": len(samples),
            "moisture": moisture.to_response(),
            "weather": weather.to_response(),
            "water_balance": water_balance.to_response(),
            "scenarios": scenarios,
        }

    def extract_moisture_features(self, png_bytes: bytes) -> MoistureFeatures:
        width, height, pixels = _decode_png_rgba(png_bytes)
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
            return MoistureFeatures(0.0, 0.0, 0.0, self.max_deficit_mm)

        moisture_score = score_sum / valid
        return MoistureFeatures(
            valid_pixel_ratio=valid / (width * height),
            moisture_score=moisture_score,
            dry_pixel_ratio=dry / valid,
            initial_water_deficit_mm=(1.0 - moisture_score) * self.max_deficit_mm,
        )

    def calculate_water_balance(
        self,
        *,
        weather: WeatherForecast,
        initial_deficit_mm: float,
        crop_coefficient: float,
        irrigation_by_day_mm: tuple[float, ...],
    ) -> WaterBalance:
        deficit = initial_deficit_mm
        daily = []
        for idx, date in enumerate(weather.daily_dates):
            previous = deficit
            et0 = weather.daily_et0_mm[idx]
            precipitation = weather.daily_precipitation_mm[idx]
            irrigation = irrigation_by_day_mm[idx] if idx < len(irrigation_by_day_mm) else 0
            deficit = _clamp(
                previous + (et0 * crop_coefficient) - precipitation - irrigation,
                lower=0.0,
                upper=self.max_deficit_mm,
            )
            daily.append(
                {
                    "date": date,
                    "previous_deficit_mm": previous,
                    "et0_mm": et0,
                    "precipitation_mm": precipitation,
                    "irrigation_mm": irrigation,
                    "deficit_mm": deficit,
                }
            )
        return WaterBalance(
            initial_deficit_mm=initial_deficit_mm,
            final_deficit_mm=deficit,
            irrigation_threshold_mm=self.irrigation_threshold_mm,
            max_deficit_mm=self.max_deficit_mm,
            daily=tuple(daily),
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

    def _build_features(
        self,
        *,
        moisture: MoistureFeatures,
        weather: WeatherForecast,
        water_balance: WaterBalance,
        crop_coefficient: float,
    ) -> dict[str, float]:
        return {
            "moisture_score": moisture.moisture_score,
            "dry_pixel_ratio": moisture.dry_pixel_ratio,
            "valid_pixel_ratio": moisture.valid_pixel_ratio,
            "initial_deficit_mm": moisture.initial_water_deficit_mm,
            "final_deficit_mm": water_balance.final_deficit_mm,
            "precipitation_7d_mm": weather.precipitation_next_7d_mm,
            "et0_7d_mm": weather.evapotranspiration_next_7d_mm,
            "avg_max_temp_7d_c": weather.avg_max_temp_next_7d_c,
            "crop_coefficient": crop_coefficient,
        }

    def _baseline_prediction(self, water_balance: WaterBalance) -> dict:
        necessity = _clamp(
            water_balance.final_deficit_mm / water_balance.max_deficit_mm
        )
        should_irrigate = water_balance.final_deficit_mm >= self.irrigation_threshold_mm
        return {
            "should_irrigate": should_irrigate,
            "urgency": _urgency(necessity),
            "necessity_score": round(necessity, 4),
            "recommended_irrigation_mm": round(
                water_balance.final_deficit_mm if should_irrigate else 0.0,
                2,
            ),
            "model_type": "fao56_fallback",
            "confidence": 0.62,
            "fallback_used": True,
        }

    def _build_irrigation_scenarios(
        self,
        *,
        moisture: MoistureFeatures,
        water_balance: WaterBalance,
        irrigation_type: str,
    ) -> list[dict]:
        delivery_efficiency = IRRIGATION_TYPE_EFFICIENCY[irrigation_type]
        ideal_effective_mm = water_balance.final_deficit_mm
        ideal_gross_mm = _gross_water_mm(ideal_effective_mm, delivery_efficiency)

        # Dry-area severity raises the conservation scenarios when more of the
        # parcel is dry, while wetter fields can safely save more water.
        dry_area_weight = _clamp(
            (moisture.dry_pixel_ratio * 0.65)
            + ((1.0 - moisture.moisture_score) * 0.35)
        )
        optimal_effective_ratio = _clamp(
            0.74 + (dry_area_weight * 0.16),
            lower=0.74,
            upper=0.9,
        )
        enough_effective_ratio = _clamp(
            0.48 + (dry_area_weight * 0.18),
            lower=0.48,
            upper=0.66,
        )

        return [
            _scenario_response(
                category="ideal",
                label="Ideal",
                effective_water_mm=ideal_effective_mm,
                ideal_effective_mm=ideal_effective_mm,
                ideal_gross_mm=ideal_gross_mm,
                delivery_efficiency=delivery_efficiency,
            ),
            _scenario_response(
                category="optimal",
                label="Optimal",
                effective_water_mm=ideal_effective_mm * optimal_effective_ratio,
                ideal_effective_mm=ideal_effective_mm,
                ideal_gross_mm=ideal_gross_mm,
                delivery_efficiency=delivery_efficiency,
            ),
            _scenario_response(
                category="enough",
                label="Enough",
                effective_water_mm=ideal_effective_mm * enough_effective_ratio,
                ideal_effective_mm=ideal_effective_mm,
                ideal_gross_mm=ideal_gross_mm,
                delivery_efficiency=delivery_efficiency,
            ),
        ]

    def _predict_with_knn(self, features: dict[str, float], samples: list[dict]) -> dict | None:
        if len(samples) < self.min_ml_samples:
            return None

        distances = sorted(
            (
                (_feature_distance(features, sample["features"]), sample)
                for sample in samples
            ),
            key=lambda item: item[0],
        )
        neighbors = distances[: min(7, len(distances))]
        weights = [1 / (distance + 1e-6) for distance, _ in neighbors]
        weight_sum = sum(weights)
        probability = sum(
            weight * (1.0 if sample["label_should_irrigate"] else 0.0)
            for weight, (_, sample) in zip(weights, neighbors)
        ) / weight_sum
        amount_mm = sum(
            weight * sample["label_irrigation_mm"]
            for weight, (_, sample) in zip(weights, neighbors)
        ) / weight_sum
        should_irrigate = probability >= 0.5
        necessity = _clamp((probability * 0.7) + ((amount_mm / self.max_deficit_mm) * 0.3))
        return {
            "should_irrigate": should_irrigate,
            "urgency": _urgency(necessity),
            "necessity_score": round(necessity, 4),
            "recommended_irrigation_mm": round(amount_mm if should_irrigate else 0.0, 2),
            "model_type": "pseudo_labeled_knn",
            "confidence": round(max(probability, 1 - probability), 4),
            "fallback_used": False,
        }

    def _reason(
        self,
        prediction: dict,
        water_balance: WaterBalance,
        fallback_used: bool,
    ) -> str:
        if fallback_used:
            source = "FAO-56 fallback"
        else:
            source = "ML model trained on local recommendation history"

        if prediction["should_irrigate"]:
            return (
                f"{source}: projected deficit is "
                f"{water_balance.final_deficit_mm:.1f} mm, above the "
                f"{self.irrigation_threshold_mm:.1f} mm threshold."
            )
        return (
            f"{source}: projected deficit is "
            f"{water_balance.final_deficit_mm:.1f} mm, below the irrigation threshold."
        )


def bbox_from_points(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    lats = [point[0] for point in points]
    lons = [point[1] for point in points]
    return (min(lons), min(lats), max(lons), max(lats))


def _irrigation_by_forecast_day(
    dates: tuple[str, ...],
    irrigation_events: list[dict],
) -> tuple[float, ...]:
    totals = {date: 0.0 for date in dates}
    for event in irrigation_events:
        applied_at = str(event.get("appliedAt", ""))
        date = applied_at[:10]
        if date in totals:
            totals[date] += float(event.get("amountMm", 0) or 0)
    return tuple(totals[date] for date in dates)


def _feature_distance(left: dict[str, float], right: dict[str, float]) -> float:
    scales = {
        "moisture_score": 1.0,
        "dry_pixel_ratio": 1.0,
        "valid_pixel_ratio": 1.0,
        "initial_deficit_mm": 60.0,
        "final_deficit_mm": 60.0,
        "precipitation_7d_mm": 50.0,
        "et0_7d_mm": 50.0,
        "avg_max_temp_7d_c": 45.0,
        "crop_coefficient": 1.5,
    }
    total = 0.0
    for key, scale in scales.items():
        total += ((left[key] - right[key]) / scale) ** 2
    return math.sqrt(total)


def _gross_water_mm(effective_water_mm: float, delivery_efficiency: float) -> float:
    if effective_water_mm <= 0:
        return 0.0
    return effective_water_mm / delivery_efficiency


def _scenario_response(
    *,
    category: str,
    label: str,
    effective_water_mm: float,
    ideal_effective_mm: float,
    ideal_gross_mm: float,
    delivery_efficiency: float,
) -> dict:
    gross_water_mm = _gross_water_mm(effective_water_mm, delivery_efficiency)
    if ideal_gross_mm <= 0:
        water_saved_mm = 0.0
        water_saved_percent = 0.0
        projected_yield_percent = 100.0
    else:
        water_saved_mm = max(0.0, ideal_gross_mm - gross_water_mm)
        water_saved_percent = _clamp(water_saved_mm / ideal_gross_mm) * 100
        effective_water_ratio = _clamp(effective_water_mm / ideal_effective_mm)
        projected_yield_percent = (
            100.0
            if category == "ideal"
            else _clamp(0.72 + (effective_water_ratio * 0.28)) * 100
        )

    return {
        "category": category,
        "label": label,
        "water_mm": round(gross_water_mm, 2),
        "effective_water_mm": round(effective_water_mm, 2),
        "water_saved_mm": round(water_saved_mm, 2),
        "water_saved_percent": round(water_saved_percent, 1),
        "projected_yield_percent": round(projected_yield_percent, 1),
    }


def _decode_png_rgba(data: bytes) -> tuple[int, int, list[tuple[int, int, int, int]]]:
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
        raise ValueError("Unsupported PNG format")

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

    pixels = []
    for row in rows:
        for idx in range(0, len(row), channels):
            alpha = row[idx + 3] if channels == 4 else 255
            pixels.append((row[idx], row[idx + 1], row[idx + 2], alpha))
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


def _urgency(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.5:
        return "medium"
    return "low"
