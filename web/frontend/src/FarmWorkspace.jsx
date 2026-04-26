import { useEffect, useState } from "react";
import MapView from "./MapView";
import LayerControls from "./LayerControls";
import { LAYERS, PRESETS } from "./config";
import { fetchIrrigationRecommendation } from "./analysisApi";
import { startSimulation, stopSimulation, completeSimulation } from "./simulationApi";
import {
  addIrrigationEvent,
  createParcel,
  getParcelAreaHectares,
  getParcelBounds,
  loadParcelsForUser,
  saveParcelsForUser,
  updateParcelPlantType,
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
  const [irrigationRecommendation, setIrrigationRecommendation] = useState(null);
  const [irrigationLoading, setIrrigationLoading] = useState(false);
  const [irrigationError, setIrrigationError] = useState(null);
  const [recommendationRefreshKey, setRecommendationRefreshKey] = useState(0);
  const [isDrawingParcel, setIsDrawingParcel] = useState(false);
  const [draftParcelPoints, setDraftParcelPoints] = useState([]);
  const [simulationRun, setSimulationRun] = useState(null);
  const [simulationLoading, setSimulationLoading] = useState(false);
  const [simulationError, setSimulationError] = useState(null);

  const selectedParcel =
    parcels.find((parcel) => parcel.id === selectedParcelId) ?? null;
  const analysisParcel =
    parcels.find((parcel) => parcel.id === analysisParcelId) ?? null;

  function persistParcels(nextParcels) {
    setParcels(nextParcels);
    saveParcelsForUser(currentUser.id, nextParcels);
  }

  useEffect(() => {
    if (!selectedParcel || isDrawingParcel) {
      setIrrigationRecommendation(null);
      setIrrigationError(null);
      setIrrigationLoading(false);
      return undefined;
    }

    let cancelled = false;
    setIrrigationLoading(true);
    setIrrigationError(null);

    fetchIrrigationRecommendation({ parcel: selectedParcel })
      .then((recommendation) => {
        if (cancelled) {
          return;
        }
        setIrrigationRecommendation(recommendation);
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }
        setIrrigationRecommendation(null);
        setIrrigationError(error.message);
      })
      .finally(() => {
        if (!cancelled) {
          setIrrigationLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [
    selectedParcel?.id,
    selectedParcel?.plantType,
    JSON.stringify(selectedParcel?.irrigationEvents ?? []),
    recommendationRefreshKey,
    isDrawingParcel,
  ]);

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
    setSimulationRun(null);
    setSimulationError(null);
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

  function handlePlantTypeChange(plantType) {
    if (!selectedParcel) {
      return;
    }

    persistParcels(updateParcelPlantType(parcels, selectedParcel.id, plantType));
  }

  function handleIrrigationTypeChange(irrigationType) {
    if (!selectedParcel) {
      return;
    }

    const nextParcels = parcels.map((p) =>
      p.id === selectedParcel.id ? { ...p, irrigationType } : p,
    );
    persistParcels(nextParcels);
  }

  function handleIrrigateSelectedParcel() {
    if (!selectedParcel) {
      return;
    }

    persistParcels(addIrrigationEvent(parcels, selectedParcel.id));
  }

  function handleRefreshRecommendation() {
    setRecommendationRefreshKey((current) => current + 1);
  }

  async function handleStartSimulation() {
    if (!selectedParcel || !irrigationRecommendation) return;
    const recommendedMm = irrigationRecommendation.recommended_irrigation_mm;
    if (!recommendedMm || recommendedMm <= 0) {
      setSimulationError("No irrigation needed right now (recommended amount is 0 mm).");
      return;
    }
    const areaHectares = getParcelAreaHectares(selectedParcel.points);
    if (areaHectares <= 0) {
      setSimulationError("Cannot compute parcel area. Try redrawing the parcel.");
      return;
    }
    setSimulationLoading(true);
    setSimulationError(null);
    try {
      const run = await startSimulation({
        parcel: {
          ...selectedParcel,
          areaHectares,
        },
        recommendedMm,
        userId: currentUser.id,
      });
      setSimulationRun(run);
    } catch (error) {
      setSimulationError(error.message);
    } finally {
      setSimulationLoading(false);
    }
  }

  async function handleStopSimulation() {
    if (!simulationRun) return;
    setSimulationLoading(true);
    try {
      const run = await stopSimulation(simulationRun.run_id);
      setSimulationRun(run);
    } catch (error) {
      setSimulationError(error.message);
    } finally {
      setSimulationLoading(false);
    }
  }

  async function handleCompleteSimulation() {
    if (!simulationRun || !selectedParcelId) return;
    setSimulationLoading(true);
    try {
      const run = await completeSimulation(simulationRun.run_id);
      setSimulationRun(run);
      const appliedMm = run.result.command_payload.target_mm;
      persistParcels(addIrrigationEvent(parcels, selectedParcelId, appliedMm));
      setRecommendationRefreshKey((k) => k + 1);
    } catch (error) {
      setSimulationError(error.message);
    } finally {
      setSimulationLoading(false);
    }
  }

  function handleDismissSimulation() {
    setSimulationRun(null);
    setSimulationError(null);
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
        irrigationRecommendation={irrigationRecommendation}
        irrigationLoading={irrigationLoading}
        irrigationError={irrigationError}
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
        onPlantTypeChange={handlePlantTypeChange}
        onIrrigationTypeChange={handleIrrigationTypeChange}
        onIrrigateSelectedParcel={handleIrrigateSelectedParcel}
        onRefreshRecommendation={handleRefreshRecommendation}
        simulationRun={simulationRun}
        simulationLoading={simulationLoading}
        simulationError={simulationError}
        onStartSimulation={handleStartSimulation}
        onStopSimulation={handleStopSimulation}
        onCompleteSimulation={handleCompleteSimulation}
        onDismissSimulation={handleDismissSimulation}
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
