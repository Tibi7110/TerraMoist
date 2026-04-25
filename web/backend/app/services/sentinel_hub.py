"""Client for the Sentinel Hub Process API hosted on CDSE."""
from __future__ import annotations

import logging
from typing import Literal

import httpx

from app.core.config import Settings
from app.services.cdse_auth import CDSETokenManager
from app.services.evalscripts import EVALSCRIPTS

logger = logging.getLogger(__name__)

IndexName = Literal["ndmi", "sar_moisture", "true_color", "vegetation_index"]

_COLLECTION_FOR_INDEX: dict[IndexName, str] = {
    "ndmi": "sentinel-2-l2a",
    "true_color": "sentinel-2-l2a",
    "vegetation_index": "sentinel-2-l2a",
    "sar_moisture": "sentinel-1-grd",
}


class SentinelHubClient:
    """Thin wrapper around the CDSE Sentinel Hub Process API."""

    def __init__(
        self,
        settings: Settings,
        token_manager: CDSETokenManager,
        client: httpx.AsyncClient,
    ):
        self._settings = settings
        self._token_manager = token_manager
        self._client = client

    async def fetch_tile_png(
        self,
        *,
        index: IndexName,
        bbox: tuple[float, float, float, float],
        date_from: str,
        date_to: str,
        width: int = 512,
        height: int = 512,
    ) -> bytes:
        payload = self._build_payload(
            index=index,
            bbox=bbox,
            date_from=date_from,
            date_to=date_to,
            width=width,
            height=height,
        )
        token = await self._token_manager.get_token()

        response = await self._client.post(
            self._settings.cdse_process_url,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "image/png",
            },
            timeout=60.0,
        )
        if response.status_code >= 400:
            logger.error(
                "Sentinel Hub error %s: %s",
                response.status_code,
                response.text[:500],
            )
            response.raise_for_status()
        return response.content

    def _build_payload(
        self,
        *,
        index: IndexName,
        bbox: tuple[float, float, float, float],
        date_from: str,
        date_to: str,
        width: int,
        height: int,
    ) -> dict:
        collection = _COLLECTION_FOR_INDEX[index]
        evalscript = EVALSCRIPTS[index]

        data_filter: dict = {
            "timeRange": {
                "from": f"{date_from}T00:00:00Z",
                "to": f"{date_to}T23:59:59Z",
            }
        }
        if collection == "sentinel-2-l2a":
            data_filter["maxCloudCoverage"] = 30
            data_filter["mosaickingOrder"] = "leastCC"
        elif collection == "sentinel-1-grd":
            data_filter["acquisitionMode"] = "IW"
            data_filter["polarization"] = "DV"
            data_filter["resolution"] = "HIGH"

        data_entry: dict = {
            "type": collection,
            "dataFilter": data_filter,
        }
        if collection == "sentinel-1-grd":
            data_entry["processing"] = {
                "backCoeff": "SIGMA0_ELLIPSOID",
                "orthorectify": True,
            }

        return {
            "input": {
                "bounds": {
                    "bbox": list(bbox),
                    "properties": {
                        "crs": "http://www.opengis.net/def/crs/EPSG/0/4326"
                    },
                },
                "data": [data_entry],
            },
            "output": {
                "width": width,
                "height": height,
                "responses": [
                    {
                        "identifier": "default",
                        "format": {"type": "image/png"},
                    }
                ],
            },
            "evalscript": evalscript,
        }
