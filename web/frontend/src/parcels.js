const PARCEL_STORAGE_PREFIX = "terramoist.parcels";
const EARTH_RADIUS_METERS = 6378137;

function storageKey(userId) {
  return `${PARCEL_STORAGE_PREFIX}.${userId}`;
}

export function loadParcelsForUser(userId) {
  const raw = window.localStorage.getItem(storageKey(userId));
  if (!raw) {
    return [];
  }

  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveParcelsForUser(userId, parcels) {
  window.localStorage.setItem(storageKey(userId), JSON.stringify(parcels));
}

export function createParcel(points, parcelCount) {
  const safeCount = parcelCount + 1;
  return {
    id: `parcel-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    name: `Parcel ${safeCount}`,
    points,
    createdAt: new Date().toISOString(),
  };
}

export function getParcelBounds(points) {
  if (!points.length) {
    return null;
  }

  const lats = points.map(([lat]) => lat);
  const lngs = points.map(([, lng]) => lng);
  return [
    [Math.min(...lats), Math.min(...lngs)],
    [Math.max(...lats), Math.max(...lngs)],
  ];
}

export function getParcelAreaHectares(points) {
  if (points.length < 3) {
    return 0;
  }

  const avgLat =
    points.reduce((sum, [lat]) => sum + lat, 0) / points.length;
  const avgLatRad = (avgLat * Math.PI) / 180;

  const projected = points.map(([lat, lng]) => {
    const latRad = (lat * Math.PI) / 180;
    const lngRad = (lng * Math.PI) / 180;
    return [
      EARTH_RADIUS_METERS * lngRad * Math.cos(avgLatRad),
      EARTH_RADIUS_METERS * latRad,
    ];
  });

  let areaMeters = 0;
  for (let index = 0; index < projected.length; index += 1) {
    const [x1, y1] = projected[index];
    const [x2, y2] = projected[(index + 1) % projected.length];
    areaMeters += x1 * y2 - x2 * y1;
  }

  return Math.abs(areaMeters / 2) / 10000;
}
