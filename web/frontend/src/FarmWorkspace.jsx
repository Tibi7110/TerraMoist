import { useState } from "react";
import MapView from "./MapView";
import LayerControls from "./LayerControls";
import { LAYERS, PRESETS } from "./config";
import {
  createParcel,
  getParcelAreaHectares,
  getParcelBounds,
  loadParcelsForUser,
  saveParcelsForUser,
} from "./parcels";

function defaultDate() {
  const d = new Date();
  d.setDate(d.getDate() - 14);
  return d.toISOString().slice(0, 10);
}

export default function FarmWorkspace({ currentUser, onLogout }) {
  const [layerId, setLayerId] = useState(LAYERS[0].id);
  const [date, setDate] = useState(defaultDate());
  const [bounds, setBounds] = useState(
    PRESETS.find((preset) => preset.id === "romania").bounds
  );
  const [parcels, setParcels] = useState(() => loadParcelsForUser(currentUser.id));
  const [selectedParcelId, setSelectedParcelId] = useState(() => {
    const savedParcels = loadParcelsForUser(currentUser.id);
    return savedParcels[0]?.id ?? null;
  });
  const [analysisParcelId, setAnalysisParcelId] = useState(null);
  const [analysisError, setAnalysisError] = useState(null);
  const [isDrawingParcel, setIsDrawingParcel] = useState(false);
  const [draftParcelPoints, setDraftParcelPoints] = useState([]);

  const selectedParcel =
    parcels.find((parcel) => parcel.id === selectedParcelId) ?? null;
  const analysisParcel =
    parcels.find((parcel) => parcel.id === analysisParcelId) ?? null;

  function persistParcels(nextParcels) {
    setParcels(nextParcels);
    saveParcelsForUser(currentUser.id, nextParcels);
  }

  function handleStartParcelDrawing() {
    setIsDrawingParcel(true);
    setDraftParcelPoints([]);
    setSelectedParcelId(null);
    setAnalysisParcelId(null);
  }

  function handleAddParcelPoint(point) {
    setDraftParcelPoints((current) => [...current, point]);
  }

  function handleUndoParcelPoint() {
    setDraftParcelPoints((current) => current.slice(0, -1));
  }

  function handleCancelParcelDrawing() {
    setIsDrawingParcel(false);
    setDraftParcelPoints([]);
  }

  function handleSaveParcel() {
    if (draftParcelPoints.length < 3) {
      return;
    }

    const parcel = createParcel(draftParcelPoints, parcels.length);
    const nextParcels = [...parcels, parcel];
    persistParcels(nextParcels);
    setSelectedParcelId(parcel.id);
    setBounds(getParcelBounds(parcel.points));
    setIsDrawingParcel(false);
    setDraftParcelPoints([]);
  }

  function handleSelectParcel(parcelId) {
    setSelectedParcelId(parcelId);
    const parcel = parcels.find((item) => item.id === parcelId);
    if (parcel) {
      setBounds(getParcelBounds(parcel.points));
    }
  }

  function handleDeleteSelectedParcel() {
    if (!selectedParcel) {
      return;
    }

    const nextParcels = parcels.filter((parcel) => parcel.id !== selectedParcel.id);
    persistParcels(nextParcels);
    if (analysisParcelId === selectedParcel.id) {
      setAnalysisParcelId(null);
    }

    const nextSelected = nextParcels[0] ?? null;
    setSelectedParcelId(nextSelected?.id ?? null);
    if (nextSelected) {
      setBounds(getParcelBounds(nextSelected.points));
    }
  }

  function handleStartAnalysis() {
    if (!selectedParcel) {
      return;
    }

    setAnalysisError(null);
    setAnalysisParcelId(selectedParcel.id);
    setBounds(getParcelBounds(selectedParcel.points));
  }

  function handleStopAnalysis() {
    setAnalysisParcelId(null);
    setAnalysisError(null);
  }

  return (
    <div className="app">
      <LayerControls
        layerId={layerId}
        onLayerChange={setLayerId}
        date={date}
        onDateChange={setDate}
        onPresetSelect={setBounds}
        currentUser={currentUser}
        onLogout={onLogout}
        parcels={parcels.map((parcel) => ({
          ...parcel,
          areaHectares: getParcelAreaHectares(parcel.points),
        }))}
        selectedParcel={selectedParcel
          ? {
              ...selectedParcel,
              areaHectares: getParcelAreaHectares(selectedParcel.points),
            }
          : null}
        selectedParcelId={selectedParcelId}
        analysisParcelId={analysisParcelId}
        analysisParcel={analysisParcel
          ? {
              ...analysisParcel,
              areaHectares: getParcelAreaHectares(analysisParcel.points),
            }
          : null}
        analysisError={analysisError}
        isDrawingParcel={isDrawingParcel}
        draftPointCount={draftParcelPoints.length}
        onStartParcelDrawing={handleStartParcelDrawing}
        onUndoParcelPoint={handleUndoParcelPoint}
        onCancelParcelDrawing={handleCancelParcelDrawing}
        onSaveParcel={handleSaveParcel}
        onSelectParcel={handleSelectParcel}
        onDeleteSelectedParcel={handleDeleteSelectedParcel}
        onStartAnalysis={handleStartAnalysis}
        onStopAnalysis={handleStopAnalysis}
      />
      <main className="map-area">
        <MapView
          layerId={layerId}
          date={date}
          bounds={bounds}
          parcels={parcels}
          selectedParcelId={selectedParcelId}
          analysisParcel={analysisParcel}
          isDrawingParcel={isDrawingParcel}
          draftParcelPoints={draftParcelPoints}
          onAddParcelPoint={handleAddParcelPoint}
          onSelectParcel={handleSelectParcel}
          onAnalysisError={setAnalysisError}
        />
      </main>
    </div>
  );
}
