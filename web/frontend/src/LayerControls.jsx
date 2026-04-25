import {
  LAYERS,
  PRESETS,
  MOISTURE_LEGEND,
  VEGETATION_LEGEND,
} from "./config";

function formatHectares(value) {
  if (value < 1) {
    return `${value.toFixed(2)} ha`;
  }
  if (value < 100) {
    return `${value.toFixed(1)} ha`;
  }
  return `${Math.round(value)} ha`;
}

export default function LayerControls({
  layerId,
  onLayerChange,
  date,
  onDateChange,
  onPresetSelect,
  currentUser,
  onLogout,
  parcels,
  selectedParcel,
  selectedParcelId,
  analysisParcelId,
  analysisParcel,
  analysisError,
  isDrawingParcel,
  draftPointCount,
  onStartParcelDrawing,
  onUndoParcelPoint,
  onCancelParcelDrawing,
  onSaveParcel,
  onSelectParcel,
  onDeleteSelectedParcel,
  onStartAnalysis,
  onStopAnalysis,
}) {
  const activeLayer = LAYERS.find((layer) => layer.id === layerId);
  const showMoistureLegend = activeLayer?.legend === "moisture";
  const showVegetationLegend = activeLayer?.legend === "vegetation";
  const analysisReady = Boolean(selectedParcel) && !isDrawingParcel;
  const analysisActive = Boolean(analysisParcelId);

  return (
    <aside className="controls">
      <header className="controls__header">
        <h1>TerraMoist</h1>
        <p className="tagline">Precision water for sustainable farming</p>
        <p className="powered">
          Powered by <strong>Copernicus Data Space Ecosystem</strong>
        </p>
        <div className="account-card">
          <div>
            <p className="account-card__label">Signed in as</p>
            <strong className="account-card__name">{currentUser.name}</strong>
            <p className="account-card__email">{currentUser.email}</p>
          </div>
          <button type="button" className="logout-btn" onClick={onLogout}>
            Logout
          </button>
        </div>
      </header>

      <section className="controls__section">
        <div className="section-heading">
          <h2>My land</h2>
          <span className="section-meta">{parcels.length} saved</span>
        </div>
        <p className="hint">
          Draw the parcel you own first. Only after selecting a saved parcel can
          you start analysis for that exact area.
        </p>

        {!isDrawingParcel ? (
          <button
            type="button"
            className="action-btn action-btn--primary"
            onClick={onStartParcelDrawing}
          >
            Start drawing
          </button>
        ) : (
          <div className="parcel-actions">
            <button
              type="button"
              className="action-btn action-btn--primary"
              onClick={onSaveParcel}
              disabled={draftPointCount < 3}
            >
              Save parcel
            </button>
            <button
              type="button"
              className="action-btn"
              onClick={onUndoParcelPoint}
              disabled={draftPointCount === 0}
            >
              Undo point
            </button>
            <button
              type="button"
              className="action-btn"
              onClick={onCancelParcelDrawing}
            >
              Cancel
            </button>
          </div>
        )}

        {isDrawingParcel && (
          <div className="drawing-card">
            <strong>Drawing in progress</strong>
            <p>
              {draftPointCount} points placed. Add at least 3 points to save
              the owned land polygon.
            </p>
          </div>
        )}

        {parcels.length > 0 ? (
          <div className="parcel-list">
            {parcels.map((parcel) => (
              <button
                key={parcel.id}
                type="button"
                className={`parcel-card ${
                  parcel.id === selectedParcelId ? "active" : ""
                }`}
                onClick={() => onSelectParcel(parcel.id)}
              >
                <strong>{parcel.name}</strong>
                <span>{formatHectares(parcel.areaHectares)}</span>
              </button>
            ))}
          </div>
        ) : (
          !isDrawingParcel && (
            <div className="empty-card">
              No saved parcels yet. Your first polygon will become the owned
              land area we analyze later.
            </div>
          )
        )}

        {selectedParcel && !isDrawingParcel && (
          <div className="selected-parcel-card">
            <p className="account-card__label">Selected parcel</p>
            <strong>{selectedParcel.name}</strong>
            <p>{formatHectares(selectedParcel.areaHectares)}</p>
            <div className="parcel-actions">
              {!analysisActive ? (
                <button
                  type="button"
                  className="action-btn action-btn--primary"
                  onClick={onStartAnalysis}
                >
                  Start analysis
                </button>
              ) : (
                <button
                  type="button"
                  className="action-btn"
                  onClick={onStopAnalysis}
                >
                  Stop analysis
                </button>
              )}
              <button
                type="button"
                className="action-btn action-btn--danger"
                onClick={onDeleteSelectedParcel}
              >
                Delete parcel
              </button>
            </div>
          </div>
        )}
      </section>

      <section className="controls__section">
        <div className="section-heading">
          <h2>Parcel analysis</h2>
          <span className={`status-pill ${analysisError ? "error" : analysisActive ? "active" : ""}`}>
            {analysisError ? "error" : analysisActive ? "running" : "idle"}
          </span>
        </div>
        {analysisError && (
          <div className="error-card">
            <strong>Eroare procesare</strong>
            <p>{analysisError}</p>
          </div>
        )}
        {analysisActive && analysisParcel && !analysisError ? (
          <div className="analysis-card">
            <strong>{analysisParcel.name}</strong>
            <p>
              Satellite processing is limited to this parcel only. Outside the
              polygon, the map stays plain.
            </p>
          </div>
        ) : (
          !analysisActive && (
            <div className="empty-card">
              Select a parcel, then click Start analysis. Until then, the map
              stays in simple base-map mode.
            </div>
          )
        )}
      </section>

      <section className={`controls__section ${!analysisReady ? "section-disabled" : ""}`}>
        <h2>Index</h2>
        <div className="layer-list">
          {LAYERS.map((layer) => (
            <button
              key={layer.id}
              className={`layer-btn ${layerId === layer.id ? "active" : ""}`}
              onClick={() => onLayerChange(layer.id)}
              disabled={!analysisReady}
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

      <section className={`controls__section ${!analysisReady ? "section-disabled" : ""}`}>
        <h2>Date</h2>
        <input
          type="date"
          value={date}
          max={new Date().toISOString().slice(0, 10)}
          onChange={(event) => onDateChange(event.target.value)}
          className="date-input"
          disabled={!analysisReady}
        />
        <p className="hint">
          We process imagery only for the active parcel, using a plus/minus
          10-day window around the selected date.
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

      {showMoistureLegend && analysisActive && (
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

      {showVegetationLegend && analysisActive && (
        <section className="controls__section">
          <h2>Legend</h2>
          <div className="legend">
            {VEGETATION_LEGEND.map((stop) => (
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
          Analysis is clipped to the selected owned parcel only.
          Outside the parcel, the map remains the plain OpenStreetMap base.
        </small>
      </footer>
    </aside>
  );
}
