"""
Rastera Engine — Geocoding Adapter
V1 default: OpenStreetMap Nominatim (free, no key required).
Swap via set_geocoder() for Google Maps, HERE, Esri, etc.

TODO adapters to implement:
  class GoogleGeocoder(GeocoderAdapter): ...
  class HereGeocoder(GeocoderAdapter): ...
  class EsriGeocoder(GeocoderAdapter): ...
"""
from abc import ABC, abstractmethod
from typing import Optional, Tuple

import httpx

from app.utils.logging import get_logger

logger = get_logger(__name__)


class GeocoderAdapter(ABC):
    """Pluggable geocoder interface. Implement geocode() to add a new provider."""

    @abstractmethod
    async def geocode(self, address: str) -> Optional[Tuple[float, float]]:
        """Return (lat, lon) in WGS84, or None if address cannot be resolved."""
        ...


class NominatimGeocoder(GeocoderAdapter):
    """
    OpenStreetMap Nominatim geocoder.
    Free for demo/low-volume use. Set a real User-Agent per OSM policy.
    """

    BASE_URL = "https://nominatim.openstreetmap.org/search"

    async def geocode(self, address: str) -> Optional[Tuple[float, float]]:
        params = {"q": address, "format": "json", "limit": 1}
        headers = {"User-Agent": "rastera-engine/1.0 (contact@rastera.io)"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(self.BASE_URL, params=params, headers=headers)
                r.raise_for_status()
                data = r.json()

            if not data:
                logger.warning("Nominatim: no result for %r", address)
                return None

            lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
            logger.info("Geocoded %r → (%.6f, %.6f)", address, lat, lon)
            return lat, lon

        except Exception as exc:
            logger.error("Geocoding failed for %r: %s", address, exc)
            return None


# ─── Module-level singleton ────────────────────────────────────────────────────
_geocoder: GeocoderAdapter = NominatimGeocoder()


def get_geocoder() -> GeocoderAdapter:
    return _geocoder


def set_geocoder(geocoder: GeocoderAdapter) -> None:
    """Replace the active geocoder at runtime (e.g. in tests or config hooks)."""
    global _geocoder
    _geocoder = geocoder
