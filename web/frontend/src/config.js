// CDSE Sentinel Hub configuration.
// The instance ID points to a public WMS configuration on the Copernicus Data
// Space Ecosystem. Tiles are fetched directly from CDSE — no proxy.
export const CDSE_INSTANCE_ID = "36aaaee0-b5f9-441e-b0f3-5d237c5bdfcd";
export const CDSE_WMS_BASE = `https://sh.dataspace.copernicus.eu/ogc/wms/${CDSE_INSTANCE_ID}`;

// Layers available in the configuration. The `id` matches the layer name in
// the Sentinel Hub configuration; the rest is UI metadata.
export const LAYERS = [
  {
    id: "MOISTURE_INDEX",
    label: "Soil Moisture (NDMI)",
    source: "Sentinel-2",
    description: "Normalized Difference Moisture Index — vegetation/soil water content.",
    legend: "moisture",
  },
  {
    id: "SAR_MOISTURE",
    label: "Soil Moisture (SAR)",
    source: "Sentinel-1",
    description: "Radar VV backscatter — direct soil-moisture proxy, works through clouds.",
    legend: "moisture",
  },
  {
    id: "TRUE_COLOR",
    label: "True Color",
    source: "Sentinel-2",
    description: "Natural color reference imagery.",
    legend: null,
  },
  {
    id: "VEGETATION_INDEX",
    label: "Vegetation (NDVI)",
    source: "Sentinel-2",
    description: "Vegetation health and density.",
    legend: "vegetation",
  },
];

// Preset regions — quick zoom shortcuts in the UI.
// Format: [name, [south, west, north, east]] (Leaflet bounds order).
export const PRESETS = [
 { id: "world",    name: "🌐 Wide view",   bounds: [[20, -10], [55, 50]] },
  { id: "europe",   name: "🇪🇺 Europe",     bounds: [[35, -15],   [60, 35]]   },
  { id: "romania",  name: "🇷🇴 Romania",    bounds: [[43.5, 20],  [48.5, 30]] },
  { id: "baragan",  name: "🌾 Bărăgan",    bounds: [[44.4, 27.0], [44.9, 27.9]] },
  { id: "dobrogea", name: "☀️ Dobrogea",   bounds: [[43.8, 28.0], [44.3, 28.7]] },
];

// NDMI / SAR moisture color ramp (matches the evalscripts in Sentinel Hub).
export const MOISTURE_LEGEND = [
  { color: "rgb(140, 69, 18)",  label: "Very dry" },
  { color: "rgb(217, 166, 33)", label: "Dry" },
  { color: "rgb(242, 230, 76)", label: "Moderate" },
  { color: "rgb(102, 191, 76)", label: "Moist" },
  { color: "rgb(26, 140, 64)",  label: "Wet" },
  { color: "rgb(26, 89, 178)",  label: "Very wet" },
];