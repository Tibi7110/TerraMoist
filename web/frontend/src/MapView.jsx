import { useEffect } from "react";
import { MapContainer, TileLayer, WMSTileLayer, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { CDSE_WMS_BASE, LAYERS } from "./config";

// Each Sentinel collection has a maximum allowed pixel size.
// Below their min-zoom, Sentinel Hub returns errors instead of tiles.
// We pad +1 to be safe (avoids occasional failures on tile edges).
const MIN_ZOOM_PER_LAYER = {
  MOISTURE_INDEX:   8,  // Sentinel-2 L2A → 1500 m/px limit
  TRUE_COLOR:       8,
  VEGETATION_INDEX: 8,
  SAR_MOISTURE:     6,  // Sentinel-1 has higher tolerance
};

function FlyToBounds({ bounds }) {
  const map = useMap();
  useEffect(() => {
    if (bounds) {
      map.flyToBounds(bounds, { duration: 1.2, maxZoom: 12 });
    }
  }, [bounds, map]);
  return null;
}

// Sentinel imagery isn't acquired daily for every spot. We request a
// ±10-day window around the user's chosen date so the mosaic engine has
// material to work with — picks the cleanest scene in that window.
function expandDateWindow(isoDate, daysEachSide = 10) {
  const d = new Date(isoDate);
  const from = new Date(d);  from.setDate(d.getDate() - daysEachSide);
  const to   = new Date(d);  to.setDate(d.getDate() + daysEachSide);
  const fmt = (x) => x.toISOString().slice(0, 10);
  return `${fmt(from)}/${fmt(to)}`;
}

export default function MapView({ layerId, date, bounds }) {
  // Re-mount the WMS layer when layer/date changes — drops the stale tile cache.
  const wmsKey = `${layerId}-${date}`;
  const minZoom = MIN_ZOOM_PER_LAYER[layerId] ?? 6;

  return (
    <MapContainer
      center={[45, 25]}
      zoom={6}
      minZoom={3}        // OSM base map allows zooming all the way out
      maxZoom={16}
      worldCopyJump
      style={{ width: "100%", height: "100%" }}
    >
      <TileLayer
        attribution='&copy; OpenStreetMap'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      <WMSTileLayer
        key={wmsKey}
        url={CDSE_WMS_BASE}
        layers={layerId}
        format="image/png"
        transparent
        version="1.3.0"
        attribution='Imagery &copy; Copernicus Data Space Ecosystem'
        params={{
          TIME: expandDateWindow(date, 10),
          MAXCC: 30,
          PRIORITY: "leastCC",
          // Stretches reflectance to a normalized RGB display.
          // Crucial for visible TRUE_COLOR / NDVI rendering.
          STYLES: layerId === "VEGETATION_INDEX" ? "INDEX" : undefined,
        }}
        opacity={0.85}
        // Tell Leaflet not to even ASK for tiles below the layer's resolution.
        // Below this, only OSM is shown — clean fallback, no error tiles.
        minZoom={minZoom}
      />

      <FlyToBounds bounds={bounds} />
    </MapContainer>
  );
}