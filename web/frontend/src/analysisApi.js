function getApiBase() {
  const base =
    import.meta.env.VITE_API_BASE ??
    `http://${window.location.hostname}:8000/api/v1`;
  return base.replace(/\/+$/, "");
}

function toIsoDateOnly(value) {
  return new Date(value).toISOString().slice(0, 10);
}

export async function fetchParcelAnalysisImage({
  analysisKey,
  parcelBounds,
  date,
}) {
  const [[south, west], [north, east]] = parcelBounds;
  const targetDate = new Date(date);
  const from = new Date(targetDate);
  const to = new Date(targetDate);
  from.setDate(targetDate.getDate() - 10);
  to.setDate(targetDate.getDate() + 10);

  const response = await fetch(`${getApiBase()}/tiles`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      index: analysisKey,
      bbox: [west, south, east, north],
      date_from: toIsoDateOnly(from),
      date_to: toIsoDateOnly(to),
      width: 1200,
      height: 1200,
    }),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? "Failed to generate parcel analysis");
  }

  const blob = await response.blob();
  return URL.createObjectURL(blob);
}

export async function fetchIrrigationRecommendation({ parcel }) {
  const response = await fetch(`${getApiBase()}/irrigation/recommend`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      fieldId: parcel.id,
      fieldName: parcel.name,
      points: parcel.points,
      plantType: parcel.plantType,
      irrigationEvents: parcel.irrigationEvents ?? [],
      lookbackDays: 10,
    }),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? "Failed to generate irrigation recommendation");
  }

  return response.json();
}
