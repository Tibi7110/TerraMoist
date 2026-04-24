"""Sentinel Hub evalscripts for TerraMoist indices.

An evalscript is a small piece of JavaScript executed inside the Sentinel Hub
processing engine. It receives per-pixel band values and returns RGB(A) output.
We keep these as plain Python strings so they can be edited without rebuilding.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# NDMI - Normalized Difference Moisture Index (Sentinel-2 L2A)
# NDMI = (B8 - B11) / (B8 + B11)
# Range ~ [-1, 1]. Higher = wetter vegetation / surface.
# Colour ramp: brown (dry) -> yellow -> green -> blue (very wet).
# ---------------------------------------------------------------------------
NDMI_EVALSCRIPT = """//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B08", "B11", "SCL", "dataMask"] }],
    output: { bands: 4 }
  };
}

function evaluatePixel(sample) {
  // Mask clouds, cloud shadows, snow, saturated pixels using the SCL band.
  // SCL legend: 3=cloud shadow, 7=unclassified, 8=cloud medium, 9=cloud high,
  //             10=cirrus, 11=snow. We keep only vegetation/soil/water classes.
  const scl = sample.SCL;
  const validScene = scl === 4 || scl === 5 || scl === 6; // veg, bare soil, water
  if (!validScene || sample.dataMask === 0) {
    return [0, 0, 0, 0]; // transparent
  }

  const ndmi = (sample.B08 - sample.B11) / (sample.B08 + sample.B11 + 1e-9);

  // Map NDMI into an intuitive dry -> wet colour ramp.
  if (ndmi < -0.2) return [0.55, 0.27, 0.07, 1]; // brown - very dry
  if (ndmi <  0.0) return [0.85, 0.65, 0.13, 1]; // tan - dry
  if (ndmi <  0.2) return [0.95, 0.90, 0.30, 1]; // yellow - moderate
  if (ndmi <  0.4) return [0.40, 0.75, 0.30, 1]; // light green - moist
  if (ndmi <  0.6) return [0.10, 0.55, 0.25, 1]; // green - wet
  return                      [0.10, 0.35, 0.70, 1]; // blue - very wet
}
"""

# ---------------------------------------------------------------------------
# Sentinel-1 VV backscatter as a soil-moisture proxy.
# Lower backscatter -> drier soil (under comparable roughness/vegetation).
# We render sigma0_VV on a log scale mapped to a dry->wet ramp.
# ---------------------------------------------------------------------------
SAR_SOIL_MOISTURE_EVALSCRIPT = """//VERSION=3
function setup() {
  return {
    input: [{ bands: ["VV", "dataMask"] }],
    output: { bands: 4 }
  };
}

function evaluatePixel(sample) {
  if (sample.dataMask === 0) return [0, 0, 0, 0];

  // Convert linear sigma0 to dB; clamp to the range typical for land surfaces.
  const vv_db = 10 * Math.log(sample.VV) / Math.LN10;
  const clamped = Math.max(-25, Math.min(0, vv_db));
  // Normalize dB range [-25, 0] -> [0, 1]  (0 = dry, 1 = wet)
  const t = (clamped + 25) / 25;

  if (t < 0.2) return [0.55, 0.27, 0.07, 1];
  if (t < 0.4) return [0.85, 0.65, 0.13, 1];
  if (t < 0.6) return [0.95, 0.90, 0.30, 1];
  if (t < 0.8) return [0.40, 0.75, 0.30, 1];
  return              [0.10, 0.35, 0.70, 1];
}
"""

# ---------------------------------------------------------------------------
# True-colour reference (Sentinel-2) - useful as a base layer and for demos.
# ---------------------------------------------------------------------------
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

# Dict lookup used by the Sentinel Hub client — maps index name to evalscript.
EVALSCRIPTS = {
    "ndmi": NDMI_EVALSCRIPT,
    "sar_moisture": SAR_SOIL_MOISTURE_EVALSCRIPT,
    "true_color": TRUE_COLOR_EVALSCRIPT,
}