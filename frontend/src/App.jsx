import { useState } from "react";
import MapView from "./MapView";
import LayerControls from "./LayerControls";
import { LAYERS, PRESETS } from "./config";
import "./App.css";

// Default to ~14 days ago — recent enough to be relevant, far back enough
// that Sentinel-2 has likely captured a clear acquisition for most areas.
function defaultDate() {
  const d = new Date();
  d.setDate(d.getDate() - 14);
  return d.toISOString().slice(0, 10);
}

export default function App() {
  const [layerId, setLayerId] = useState(LAYERS[0].id);
  const [date, setDate] = useState(defaultDate());
  // Initial view — Romania, since that's our demo target.
  const [bounds, setBounds] = useState(
    PRESETS.find((p) => p.id === "romania").bounds
  );

  return (
    <div className="app">
      <LayerControls
        layerId={layerId}
        onLayerChange={setLayerId}
        date={date}
        onDateChange={setDate}
        onPresetSelect={setBounds}
      />
      <main className="map-area">
        <MapView layerId={layerId} date={date} bounds={bounds} />
      </main>
    </div>
  );
}