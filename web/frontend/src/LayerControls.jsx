import { LAYERS, PRESETS, MOISTURE_LEGEND } from "./config";

// Controls panel: layer picker, date input, preset region buttons, legend.
// Pure presentational component — state lives in App.
export default function LayerControls({
  layerId, onLayerChange,
  date, onDateChange,
  onPresetSelect,
}) {
  const activeLayer = LAYERS.find((l) => l.id === layerId);
  const showMoistureLegend = activeLayer?.legend === "moisture";

  return (
    <aside className="controls">
      <header className="controls__header">
        <h1>TerraMoist</h1>
        <p className="tagline">Precision water for sustainable farming</p>
        <p className="powered">
          Powered by <strong>Copernicus Data Space Ecosystem</strong>
        </p>
      </header>

      <section className="controls__section">
        <h2>Index</h2>
        <div className="layer-list">
          {LAYERS.map((layer) => (
            <button
              key={layer.id}
              className={`layer-btn ${layerId === layer.id ? "active" : ""}`}
              onClick={() => onLayerChange(layer.id)}
            >
              <div className="layer-btn__title">{layer.label}</div>
              <div className="layer-btn__source">{layer.source}</div>
            </button>
          ))}
        </div>
        {activeLayer && (
          <p className="layer-description">{activeLayer.description}</p>
        )}
      </section>

      <section className="controls__section">
        <h2>Date</h2>
        <input
          type="date"
          value={date}
          max={new Date().toISOString().slice(0, 10)}
          onChange={(e) => onDateChange(e.target.value)}
          className="date-input"
        />
        <p className="hint">
          Imagery is fetched on-the-fly. We use a ±10-day window around the
          selected date to find the clearest scene.
        </p>
      </section>

      <section className="controls__section">
        <h2>Quick zoom</h2>
        <div className="preset-grid">
          {PRESETS.map((preset) => (
            <button
              key={preset.id}
              className="preset-btn"
              onClick={() => onPresetSelect(preset.bounds)}
            >
              {preset.name}
            </button>
          ))}
        </div>
      </section>

      {showMoistureLegend && (
        <section className="controls__section">
          <h2>Legend</h2>
          <div className="legend">
            {MOISTURE_LEGEND.map((stop) => (
              <div key={stop.label} className="legend-row">
                <span
                  className="legend-swatch"
                  style={{ background: stop.color }}
                />
                <span>{stop.label}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      <footer className="controls__footer">
        <small>
          Sentinel-1 &amp; Sentinel-2 imagery via Copernicus.
          NDMI / SAR backscatter computed on-the-fly.
        </small>
      </footer>
    </aside>
  );
}