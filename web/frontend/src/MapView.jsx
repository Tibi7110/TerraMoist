import { useEffect, useRef, useState } from "react";
import {
  CircleMarker,
  ImageOverlay,
  MapContainer,
  Polygon,
  Polyline,
  TileLayer,
  Tooltip,
  useMap,
  useMapEvents,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { LAYERS } from "./config";
import { fetchParcelAnalysisImage } from "./analysisApi";
import { getParcelBounds } from "./parcels";

function FlyToBounds({ bounds }) {
  const map = useMap();

  useEffect(() => {
    if (bounds) {
      map.flyToBounds(bounds, { duration: 1.2, maxZoom: 15, padding: [30, 30] });
    }
  }, [bounds, map]);

  return null;
}

function MapDrawingHandler({ isDrawingParcel, onAddParcelPoint }) {
  const map = useMapEvents({
    click(event) {
      if (!isDrawingParcel) {
        return;
      }

      onAddParcelPoint([event.latlng.lat, event.latlng.lng]);
    },
  });

  useEffect(() => {
    const container = map.getContainer();
    container.style.cursor = isDrawingParcel ? "crosshair" : "";

    return () => {
      container.style.cursor = "";
    };
  }, [isDrawingParcel, map]);

  return null;
}

function ParcelAnalysisOverlay({ parcel, layerId, date, onAnalysisError }) {
  const map = useMap();
  const overlayRef = useRef(null);
  const objectUrlRef = useRef("");
  const [imageUrl, setImageUrl] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const parcelBounds = getParcelBounds(parcel.points);
  const parcelBoundsKey = JSON.stringify(parcelBounds);
  const parcelPointsKey = JSON.stringify(parcel.points);
  const activeLayer = LAYERS.find((layer) => layer.id === layerId);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    setImageUrl("");
    const currentBounds = JSON.parse(parcelBoundsKey);

    fetchParcelAnalysisImage({
      analysisKey: activeLayer.analysisKey,
      parcelBounds: currentBounds,
      date,
    })
      .then((nextUrl) => {
        if (cancelled) {
          URL.revokeObjectURL(nextUrl);
          return;
        }

        if (objectUrlRef.current) {
          URL.revokeObjectURL(objectUrlRef.current);
        }
        objectUrlRef.current = nextUrl;
        setError("");
        setLoading(false);
        setImageUrl(nextUrl);
        onAnalysisError(null);
      })
      .catch((requestError) => {
        if (cancelled) {
          return;
        }
        setLoading(false);
        setError(requestError.message);
        onAnalysisError(requestError.message);
      });

    return () => {
      cancelled = true;
    };
  }, [activeLayer.analysisKey, date, parcelBoundsKey]);

  useEffect(() => {
    return () => {
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!imageUrl || !overlayRef.current) {
      return undefined;
    }

    const overlay = overlayRef.current;
    const currentBounds = JSON.parse(parcelBoundsKey);
    const currentPoints = JSON.parse(parcelPointsKey);

    function applyClipPath() {
      const image = overlay.getElement();
      if (!image) {
        return;
      }

      const [[south, west], [north, east]] = currentBounds;
      const topLeft = map.latLngToLayerPoint([north, west]);
      const bottomRight = map.latLngToLayerPoint([south, east]);
      const width = bottomRight.x - topLeft.x;
      const height = bottomRight.y - topLeft.y;

      if (width <= 0 || height <= 0) {
        return;
      }

      const polygon = currentPoints.map(([lat, lng]) => {
        const point = map.latLngToLayerPoint([lat, lng]);
        const x = ((point.x - topLeft.x) / width) * 100;
        const y = ((point.y - topLeft.y) / height) * 100;
        return `${x}% ${y}%`;
      });

      const clipPath = `polygon(${polygon.join(",")})`;
      image.style.clipPath = clipPath;
      image.style.webkitClipPath = clipPath;
      image.style.pointerEvents = "none";
    }

    overlay.on("load", applyClipPath);
    map.on("zoom move resize", applyClipPath);
    applyClipPath();

    return () => {
      overlay.off("load", applyClipPath);
      map.off("zoom move resize", applyClipPath);
    };
  }, [imageUrl, map, parcelBoundsKey, parcelPointsKey]);

  return (
    <>
      {imageUrl && (
        <ImageOverlay
          ref={overlayRef}
          url={imageUrl}
          bounds={parcelBounds}
          opacity={0.9}
        />
      )}
      {loading && !error && (
        <Polygon
          positions={parcel.points}
          pathOptions={{
            color: "#f7c948",
            weight: 3,
            dashArray: "6 6",
            fillColor: "#f7c948",
            fillOpacity: 0.05,
          }}
        >
          <Tooltip permanent>Se incarca imaginea satelit...</Tooltip>
        </Polygon>
      )}
      {error && (
        <Polygon
          positions={parcel.points}
          pathOptions={{
            color: "#ff9b9b",
            weight: 3,
            dashArray: "6 6",
            fillOpacity: 0,
          }}
        >
          <Tooltip sticky>{error}</Tooltip>
        </Polygon>
      )}
    </>
  );
}

export default function MapView({
  layerId,
  date,
  bounds,
  parcels,
  selectedParcelId,
  analysisParcel,
  isDrawingParcel,
  draftParcelPoints,
  onAddParcelPoint,
  onSelectParcel,
  onAnalysisError,
}) {
  return (
    <MapContainer
      center={[45, 25]}
      zoom={6}
      minZoom={3}
      maxZoom={16}
      worldCopyJump
      className={isDrawingParcel ? "map-canvas map-canvas--drawing" : "map-canvas"}
      style={{ width: "100%", height: "100%" }}
    >
      <TileLayer
        attribution="&copy; OpenStreetMap"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {analysisParcel && (
        <ParcelAnalysisOverlay
          parcel={analysisParcel}
          layerId={layerId}
          date={date}
          onAnalysisError={onAnalysisError ?? (() => {})}
        />
      )}

      {parcels.map((parcel) => {
        const isSelected = parcel.id === selectedParcelId;
        const isAnalysisParcel = analysisParcel?.id === parcel.id;

        return (
          <Polygon
            key={parcel.id}
            positions={parcel.points}
            pathOptions={{
              color: isAnalysisParcel
                ? "#f7c948"
                : isSelected
                  ? "#8df0a7"
                  : "#58a6ff",
              weight: isAnalysisParcel ? 4 : isSelected ? 4 : 3,
              fillColor: isAnalysisParcel
                ? "#f7c948"
                : isSelected
                  ? "#2ea043"
                  : "#58a6ff",
              fillOpacity: isAnalysisParcel ? 0.08 : isSelected ? 0.12 : 0.06,
            }}
            eventHandlers={{
              click: () => onSelectParcel(parcel.id),
            }}
          >
            <Tooltip sticky>
              {isAnalysisParcel ? `${parcel.name} · analysis active` : parcel.name}
            </Tooltip>
          </Polygon>
        );
      })}

      {isDrawingParcel && draftParcelPoints.length >= 2 && (
        <Polyline
          positions={draftParcelPoints}
          pathOptions={{
            color: "#f7c948",
            weight: 3,
            dashArray: "8 8",
          }}
        />
      )}

      {isDrawingParcel && draftParcelPoints.length >= 3 && (
        <Polygon
          positions={draftParcelPoints}
          pathOptions={{
            color: "#f7c948",
            weight: 3,
            fillColor: "#f7c948",
            fillOpacity: 0.18,
            dashArray: "8 8",
          }}
        />
      )}

      {isDrawingParcel &&
        draftParcelPoints.map((point, index) => (
          <CircleMarker
            key={`${point[0]}-${point[1]}-${index}`}
            center={point}
            radius={6}
            pathOptions={{
              color: "#fff4c2",
              weight: 2,
              fillColor: "#f7c948",
              fillOpacity: 1,
            }}
          >
            <Tooltip direction="top" offset={[0, -4]} opacity={0.92}>
              Point {index + 1}
            </Tooltip>
          </CircleMarker>
        ))}

      <MapDrawingHandler
        isDrawingParcel={isDrawingParcel}
        onAddParcelPoint={onAddParcelPoint}
      />
      <FlyToBounds bounds={bounds} />
    </MapContainer>
  );
}
