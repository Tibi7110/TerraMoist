"""Predefined agricultural regions for demos and testing.

Bounding boxes are (min_lon, min_lat, max_lon, max_lat) in EPSG:4326.
"""
from __future__ import annotations

# Bărăgan Plain is Romania's main cereal-producing region, east of Bucharest.
# It's ideal for a soil-moisture demo: large flat fields, seasonal irrigation,
# clear contrast between dry summer and wetter spring.
PRESETS: dict[str, dict] = {
    "baragan": {
        "name": "Bărăgan Plain",
        "description": "Romania's main cereal belt (Ialomița / Brăila / Călărași).",
        "bbox": (27.0, 44.4, 27.9, 44.9),
    },
    "baragan_small": {
        "name": "Bărăgan — demo field cluster",
        "description": "Small zoomed-in window for fast live demos.",
        "bbox": (27.30, 44.55, 27.50, 44.70),
    },
    "dobrogea": {
        "name": "Dobrogea South",
        "description": "Arid agricultural zone in south-east Romania.",
        "bbox": (28.0, 43.8, 28.7, 44.3),
    },
}