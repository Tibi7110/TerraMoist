export const LAYERS = [
  {
    id: "MOISTURE_INDEX",
    label: "Soil Moisture (NDMI)",
    source: "Sentinel-2",
    description: "Normalized Difference Moisture Index for vegetation and surface water content.",
    analysisKey: "ndmi",
    legend: "moisture",
  },
  {
    id: "SAR_MOISTURE",
    label: "Soil Moisture (SAR)",
    source: "Sentinel-1",
    description: "Radar VV backscatter as a direct soil-moisture proxy through clouds.",
    analysisKey: "sar_moisture",
    legend: "moisture",
  },
  {
    id: "TRUE_COLOR",
    label: "True Color",
    source: "Sentinel-2",
    description: "Natural color reference imagery for the selected parcel.",
    analysisKey: "true_color",
    legend: null,
  },
  {
    id: "VEGETATION_INDEX",
    label: "Vegetation (NDVI)",
    source: "Sentinel-2",
    description: "Vegetation vigor and density for the active parcel.",
    analysisKey: "vegetation_index",
    legend: "vegetation",
  },
];

export const PRESETS = [
  { id: "world", name: "Wide view", bounds: [[20, -10], [55, 50]] },
  { id: "europe", name: "Europe", bounds: [[35, -15], [60, 35]] },
  { id: "romania", name: "Romania", bounds: [[43.5, 20], [48.5, 30]] },
  { id: "baragan", name: "Baragan", bounds: [[44.4, 27.0], [44.9, 27.9]] },
  { id: "dobrogea", name: "Dobrogea", bounds: [[43.8, 28.0], [44.3, 28.7]] },
];

export const MOISTURE_LEGEND = [
  { color: "rgb(140, 69, 18)", label: "Very dry" },
  { color: "rgb(217, 166, 33)", label: "Dry" },
  { color: "rgb(242, 230, 76)", label: "Moderate" },
  { color: "rgb(102, 191, 76)", label: "Moist" },
  { color: "rgb(26, 140, 64)", label: "Wet" },
  { color: "rgb(26, 89, 178)", label: "Very wet" },
];

export const VEGETATION_LEGEND = [
  { color: "rgb(115, 74, 41)", label: "Bare / weak" },
  { color: "rgb(199, 168, 87)", label: "Low vigor" },
  { color: "rgb(178, 201, 87)", label: "Developing" },
  { color: "rgb(84, 176, 69)", label: "Healthy" },
  { color: "rgb(20, 117, 46)", label: "Very dense" },
];
