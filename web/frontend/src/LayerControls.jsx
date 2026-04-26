import {
  LAYERS,
  PRESETS,
  PLANT_TYPES,
  IRRIGATION_TYPES,
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

function formatLastIrrigation(irrigationEvents = []) {
  const lastEvent = irrigationEvents.at(-1);
  if (!lastEvent) {
    return "No irrigation recorded yet";
  }

  const date = new Date(lastEvent.appliedAt).toLocaleDateString();
  return `Last irrigation: ${lastEvent.amountMm} mm on ${date}`;
}

function formatPercent(value) {
  return `${Math.round(value * 100)}%`;
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
  irrigationRecommendation,
  irrigationLoading,
  irrigationError,
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
  onPlantTypeChange,
  onIrrigationTypeChange,
  onIrrigateSelectedParcel,
  onRefreshRecommendation,
  simulationRun,
  simulationLoading,
  simulationError,
  onStartSimulation,
  onStopSimulation,
  onCompleteSimulation,
  onDismissSimulation,
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

            <label className="parcel-field">
              <span>Plant type</span>
              <select
                value={selectedParcel.plantType}
                onChange={(event) => onPlantTypeChange(event.target.value)}
              >
                {PLANT_TYPES.map((plant) => (
                  <option key={plant.id} value={plant.id}>
                    {plant.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="parcel-field">
              <span>Irrigation Type</span>
              <select
                value={selectedParcel.irrigationType || "fixed"}
                onChange={(event) =>
                  onIrrigationTypeChange(event.target.value)
                }
              >
                {IRRIGATION_TYPES.map((type) => (
                  <option key={type.id} value={type.id}>
                    {type.label}
                  </option>
                ))}
              </select>
            </label>

            <p className="irrigation-note">
              {formatLastIrrigation(selectedParcel.irrigationEvents)}
            </p>

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
                className="action-btn action-btn--water"
                onClick={onIrrigateSelectedParcel}
                disabled={irrigationLoading}
              >
                Start irrigation
              </button>
              <button
                type="button"
                className="action-btn"
                onClick={onRefreshRecommendation}
                disabled={irrigationLoading}
              >
                Refresh advice
              </button>
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

      <section className="controls__section">
        <div className="section-heading">
          <h2>Irrigation advice</h2>
          <span className={`status-pill ${
            irrigationError
              ? "error"
              : irrigationRecommendation?.should_irrigate
                ? "active"
                : ""
          }`}>
            {irrigationError
              ? "error"
              : irrigationLoading
                ? "loading"
                : irrigationRecommendation?.urgency ?? "idle"}
          </span>
        </div>

        {irrigationError && (
          <div className="error-card">
            <strong>Recommendation failed</strong>
            <p>{irrigationError}</p>
          </div>
        )}

        {irrigationLoading && !irrigationRecommendation && !irrigationError && (
          <div className="empty-card">
            Training on history and fetching current satellite/weather data.
          </div>
        )}

        {irrigationRecommendation && !irrigationError && (
          <div className="recommendation-card">
            <div className="recommendation-card__main">
              <strong>
                {irrigationRecommendation.should_irrigate
                  ? "Irrigate"
                  : "Hold irrigation"}
              </strong>
              <span>
                {formatPercent(irrigationRecommendation.necessity_score)} need
              </span>
            </div>
            <dl className="recommendation-metrics">
              <div>
                <dt>Amount</dt>
                <dd>{irrigationRecommendation.recommended_irrigation_mm} mm</dd>
              </div>
              <div>
                <dt>Urgency</dt>
                <dd>{irrigationRecommendation.urgency}</dd>
              </div>
              <div>
                <dt>Model</dt>
                <dd>{irrigationRecommendation.model_type}</dd>
              </div>
              <div>
                <dt>Samples</dt>
                <dd>{irrigationRecommendation.training_samples}</dd>
              </div>
            </dl>
            <p>{irrigationRecommendation.reason}</p>
          </div>
        )}
      </section>

      <section className="controls__section">
        <div className="section-heading">
          <h2>ESP32 Control</h2>
          <span className={`status-pill ${
            simulationError ? "error" :
            simulationRun?.state === "running" ? "active" :
            simulationRun?.state === "completed" ? "completed" : ""
          }`}>
            {simulationError ? "error" :
             simulationRun?.state ?? "idle"}
          </span>
        </div>

        {simulationError && (
          <div className="error-card">
            <strong>Simulation error</strong>
            <p>{simulationError}</p>
            <button type="button" className="action-btn" onClick={onDismissSimulation}>
              Dismiss
            </button>
          </div>
        )}

        {!simulationRun && !simulationError && (
          irrigationRecommendation ? (
            <div>
              <p className="hint">
                Send the irrigation command to the ESP32 device based on the current recommendation.
              </p>
              <button
                type="button"
                className="action-btn action-btn--primary"
                onClick={onStartSimulation}
                disabled={simulationLoading}
              >
                {simulationLoading ? "Starting…" : "Start ESP32 irrigation"}
              </button>
            </div>
          ) : (
            <div className="empty-card">
              Run irrigation advice first, then start the ESP32 simulation.
            </div>
          )
        )}

        {simulationRun && !simulationError && (
          <div className="simulation-card">
            <div className="simulation-card__header">
              <strong>{simulationRun.result.command_payload.parcel_name}</strong>
              <span className={`run-state run-state--${simulationRun.state}`}>
                {simulationRun.state}
              </span>
            </div>

            <dl className="recommendation-metrics">
              <div>
                <dt>Water volume</dt>
                <dd>{(simulationRun.result.water_volume_liters / 1000).toLocaleString(undefined, { maximumFractionDigits: 1 })} m³</dd>
              </div>
              <div>
                <dt>Duration</dt>
                <dd>~{(simulationRun.result.estimated_duration_minutes / 60).toLocaleString(undefined, { maximumFractionDigits: 1 })} h</dd>
              </div>
              <div>
                <dt>Zones</dt>
                <dd>{simulationRun.result.command_payload.zone_count}</dd>
              </div>
              <div>
                <dt>System</dt>
                <dd>{simulationRun.result.command_payload.irrigation_system_type}</dd>
              </div>
              <div>
                <dt>Water saved</dt>
                <dd>{(simulationRun.result.estimated_water_saved_liters / 1000).toLocaleString(undefined, { maximumFractionDigits: 1 })} m³</dd>
              </div>
              <div>
                <dt>Target</dt>
                <dd>{simulationRun.result.command_payload.target_mm} mm</dd>
              </div>
            </dl>

            <p className="hint simulation-topic">
              MQTT: <code>{simulationRun.result.topic}</code>
            </p>

            {simulationRun.state === "running" && (
              <div className="parcel-actions">
                <button
                  type="button"
                  className="action-btn action-btn--primary"
                  onClick={onCompleteSimulation}
                  disabled={simulationLoading}
                >
                  Mark complete
                </button>
                <button
                  type="button"
                  className="action-btn action-btn--danger"
                  onClick={onStopSimulation}
                  disabled={simulationLoading}
                >
                  Stop irrigation
                </button>
              </div>
            )}

            {simulationRun.state !== "running" && (
              <button
                type="button"
                className="action-btn"
                onClick={onDismissSimulation}
              >
                New simulation
              </button>
            )}
          </div>
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

      


      <footer className="controls__footer">
        <small>
          Analysis is clipped to the selected owned parcel only.
          Outside the parcel, the map remains the plain OpenStreetMap base.
        </small>
      </footer>
    </aside>
  );
}
