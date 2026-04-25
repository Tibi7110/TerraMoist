"""Sentinel Hub evalscripts for TerraMoist indices."""
from __future__ import annotations

NDMI_EVALSCRIPT = """//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B08", "B11", "SCL", "dataMask"] }],
    output: { bands: 4 }
  };
}

function evaluatePixel(sample) {
  const scl = sample.SCL;
  const validScene = scl === 4 || scl === 5 || scl === 6;
  if (!validScene || sample.dataMask === 0) {
    return [0, 0, 0, 0];
  }

  const ndmi = (sample.B08 - sample.B11) / (sample.B08 + sample.B11 + 1e-9);

  if (ndmi < -0.2) return [0.55, 0.27, 0.07, 1];
  if (ndmi <  0.0) return [0.85, 0.65, 0.13, 1];
  if (ndmi <  0.2) return [0.95, 0.90, 0.30, 1];
  if (ndmi <  0.4) return [0.40, 0.75, 0.30, 1];
  if (ndmi <  0.6) return [0.10, 0.55, 0.25, 1];
  return [0.10, 0.35, 0.70, 1];
}
"""

SAR_SOIL_MOISTURE_EVALSCRIPT = """//VERSION=3
function setup() {
  return {
    input: [{ bands: ["VV", "dataMask"] }],
    output: { bands: 4 }
  };
}

function evaluatePixel(sample) {
  if (sample.dataMask === 0) return [0, 0, 0, 0];

  const vv_db = 10 * Math.log(sample.VV) / Math.LN10;
  const clamped = Math.max(-25, Math.min(0, vv_db));
  const t = (clamped + 25) / 25;

  if (t < 0.2) return [0.55, 0.27, 0.07, 1];
  if (t < 0.4) return [0.85, 0.65, 0.13, 1];
  if (t < 0.6) return [0.95, 0.90, 0.30, 1];
  if (t < 0.8) return [0.40, 0.75, 0.30, 1];
  return [0.10, 0.35, 0.70, 1];
}
"""

TRUE_COLOR_EVALSCRIPT = """//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B02", "B03", "B04", "dataMask"] }],
    output: { bands: 4 }
  };
}

function evaluatePixel(sample) {
  return [
    2.5 * sample.B04,
    2.5 * sample.B03,
    2.5 * sample.B02,
    sample.dataMask
  ];
}
"""

VEGETATION_INDEX_EVALSCRIPT = """//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B04", "B08", "SCL", "dataMask"] }],
    output: { bands: 4 }
  };
}

function evaluatePixel(sample) {
  const scl = sample.SCL;
  const validScene = scl === 4 || scl === 5 || scl === 6;
  if (!validScene || sample.dataMask === 0) {
    return [0, 0, 0, 0];
  }

  const ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04 + 1e-9);

  if (ndvi < 0.0) return [0.45, 0.29, 0.16, 1];
  if (ndvi < 0.2) return [0.78, 0.66, 0.34, 1];
  if (ndvi < 0.4) return [0.70, 0.79, 0.34, 1];
  if (ndvi < 0.6) return [0.33, 0.69, 0.27, 1];
  return [0.08, 0.46, 0.18, 1];
}
"""

EVALSCRIPTS = {
    "ndmi": NDMI_EVALSCRIPT,
    "sar_moisture": SAR_SOIL_MOISTURE_EVALSCRIPT,
    "true_color": TRUE_COLOR_EVALSCRIPT,
    "vegetation_index": VEGETATION_INDEX_EVALSCRIPT,
}
