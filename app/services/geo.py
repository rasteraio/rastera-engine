"""
Rastera Engine — Geospatial Operations
- Trade area polygon generation (radius buffer; drive-time TODO)
- PostGIS POI spatial query
- Competitor + market summary helpers
"""
from typing import Any, Dict, List

from shapely.geometry import Point, mapping
from shapely.ops import transform
import pyproj
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.utils.logging import get_logger

logger = get_logger(__name__)

# ─── Projection helpers ───────────────────────────────────────────────────────
_wgs84 = pyproj.CRS("EPSG:4326")
_mercator = pyproj.CRS("EPSG:3857")
_to_mercator = pyproj.Transformer.from_crs(_wgs84, _mercator, always_xy=True).transform
_to_wgs84 = pyproj.Transformer.from_crs(_mercator, _wgs84, always_xy=True).transform


# ─── Trade Area ───────────────────────────────────────────────────────────────

def compute_trade_area_geojson(lat: float, lon: float, radius_m: float) -> Dict[str, Any]:
    """
    Build a metre-accurate circular buffer polygon around (lat, lon) and return
    it as a GeoJSON Feature (WGS84).

    TODO: Replace with drive-time isochrone via Valhalla or OSRM when
          accurate travel-time trade areas are required.
    """
    point_wgs = Point(lon, lat)
    point_merc = transform(_to_mercator, point_wgs)
    buffer_merc = point_merc.buffer(radius_m, resolution=32)
    buffer_wgs = transform(_to_wgs84, buffer_merc)

    return {
        "type": "Feature",
        "geometry": mapping(buffer_wgs),
        "properties": {
            "radius_m": radius_m,
            "center_lat": lat,
            "center_lon": lon,
            "method": "radius_buffer",  # swap to "drive_time" in V2
        },
    }


# ─── POI Spatial Query ────────────────────────────────────────────────────────

async def get_pois_in_radius(
    db: AsyncSession,
    lat: float,
    lon: float,
    radius_m: float,
    tenant_id: str,
) -> List[Dict[str, Any]]:
    """
    Return all POIs for tenant_id within radius_m metres of (lat, lon).
    Uses PostGIS ST_DWithin on the geography type for accurate spherical distance.
    """
    sql = text("""
        SELECT
            p.id,
            p.name,
            p.category,
            p.brand,
            ST_Y(p.geom::geometry)  AS poi_lat,
            ST_X(p.geom::geometry)  AS poi_lon,
            ST_Distance(
                p.geom::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
            ) AS distance_m
        FROM pois p
        WHERE
            p.tenant_id = :tenant_id
            AND ST_DWithin(
                p.geom::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                :radius_m
            )
        ORDER BY distance_m
    """)

    result = await db.execute(
        sql,
        {"lat": lat, "lon": lon, "radius_m": radius_m, "tenant_id": tenant_id},
    )
    rows = result.fetchall()

    pois = [
        {
            "id": str(row.id),
            "name": row.name,
            "category": row.category,
            "brand": row.brand,
            "lat": row.poi_lat,
            "lon": row.poi_lon,
            "distance_m": round(row.distance_m, 1),
        }
        for row in rows
    ]
    logger.debug("Found %d POIs within %.0fm for tenant=%s", len(pois), radius_m, tenant_id)
    return pois


# ─── Summarisers ──────────────────────────────────────────────────────────────

def summarize_competitors(pois: List[Dict], industry_template: str) -> Dict[str, int]:
    """Count POIs by category."""
    summary: Dict[str, int] = {}
    for poi in pois:
        cat = poi["category"]
        summary[cat] = summary.get(cat, 0) + 1
    return dict(sorted(summary.items(), key=lambda x: -x[1]))


def compute_market_summary(
    pois: List[Dict],
    lat: float,
    lon: float,
    radius_m: float,
) -> Dict[str, Any]:
    """
    Derive a synthetic market proxy from POI density and foot-traffic mix.

    TODO: Replace or augment with real demographics sources:
      - US Census ACS (population, income)
      - Esri Demographics API
      - Daytime population from SafeGraph / Veraset
    """
    total_pois = len(pois)
    area_km2 = 3.14159 * (radius_m / 1000) ** 2
    poi_density = round(total_pois / area_km2, 2) if area_km2 else 0

    foot_traffic_cats = {"fast_food", "grocery", "convenience", "bakery", "retail"}
    foot_traffic_count = sum(1 for p in pois if p["category"] in foot_traffic_cats)

    market_activity_score = min(100, int(poi_density * 10 + foot_traffic_count * 2))

    return {
        "total_pois_in_radius": total_pois,
        "poi_density_per_km2": poi_density,
        "area_km2": round(area_km2, 3),
        "foot_traffic_indicators": foot_traffic_count,
        "market_activity_score": market_activity_score,
        # ── Placeholder fields for future real demographics ────────────
        # "population_5min_drive": None,      # TODO: Census / Esri
        # "median_household_income": None,    # TODO: ACS
        # "daytime_population": None,         # TODO: mobility data
    }
