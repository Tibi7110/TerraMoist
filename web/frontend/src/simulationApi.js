function getApiBase() {
  const base = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000/api/v1";
  return base.replace(/\/+$/, "");
}

function extractErrorMessage(detail, fallback) {
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((e) => `${(e.loc ?? []).slice(1).join(".")}: ${e.msg}`)
      .join(" | ");
  }
  return fallback;
}

function bboxFromParcel(parcel) {
  const lats = parcel.points.map(([lat]) => lat);
  const lngs = parcel.points.map(([, lng]) => lng);
  const south = Math.min(...lats);
  const north = Math.max(...lats);
  const west = Math.min(...lngs);
  const east = Math.max(...lngs);
  return [west, south, east, north];
}

function toSimulareSystemType(irrigationType) {
  return irrigationType === "moving" ? "mobile" : "fixed";
}

export async function startSimulation({ parcel, recommendedMm, userId }) {
  const response = await fetch(`${getApiBase()}/simulare/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      farmer_id: String(userId),
      parcel_id: parcel.id,
      parcel_name: parcel.name,
      bbox: bboxFromParcel(parcel),
      area_hectares: parcel.areaHectares,
      recommended_irrigation_mm: recommendedMm,
      irrigation_system_type: toSimulareSystemType(parcel.irrigationType),
      subscription_plan: "basic",
    }),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(extractErrorMessage(payload?.detail, "Failed to start ESP32 simulation"));
  }
  return response.json();
}

export async function stopSimulation(runId) {
  const response = await fetch(`${getApiBase()}/simulare/${runId}/stop`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason: "manual-stop" }),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(extractErrorMessage(payload?.detail, "Failed to stop simulation"));
  }
  return response.json();
}

export async function completeSimulation(runId) {
  const response = await fetch(`${getApiBase()}/simulare/${runId}/complete`, {
    method: "POST",
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(extractErrorMessage(payload?.detail, "Failed to complete simulation"));
  }
  return response.json();
}
