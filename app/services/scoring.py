"""
Rastera Engine — V1 Scoring Model
Weighted sum of 5 interpretable drivers → composite score 0–100.

Driver weights:
  1. Competitor Pressure     max  20 pts  (fewer direct competitors = higher)
  2. Category Mix            max  20 pts  (complementary categories present)
  3. Market Density          max  25 pts  (POI density as activity proxy)
  4. Foot Traffic Potential  max  20 pts  (adjacent foot-traffic generators)
  5. Brand Gap               max  15 pts  (underserved = higher gap score)
                             ─────────
  Max possible               =  100 pts

TODO: V2 scoring additions
  - Drive-time accessibility score (Valhalla isochrone area)
  - Real demographics weighting (income, population density)
  - Competitor brand quality weighting (chain vs. independent)
  - Seasonal / daytime population adjustments
"""
from typing import Any, Dict, List, Tuple

from app.utils.logging import get_logger

logger = get_logger(__name__)

# ─── Industry Templates ────────────────────────────────────────────────────────

INDUSTRY_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "coffee": {
        "competitor_category": "coffee",
        "complementary_categories": ["grocery", "bakery", "office", "retail"],
        "foot_traffic_categories": ["fast_food", "grocery", "convenience"],
    },
    "restaurant": {
        "competitor_category": "restaurant",
        "complementary_categories": ["retail", "office", "grocery"],
        "foot_traffic_categories": ["fast_food", "grocery", "convenience"],
    },
    "retail": {
        "competitor_category": "retail",
        "complementary_categories": ["grocery", "restaurant", "coffee"],
        "foot_traffic_categories": ["grocery", "fast_food", "coffee"],
    },
    "grocery": {
        "competitor_category": "grocery",
        "complementary_categories": ["bakery", "coffee", "restaurant"],
        "foot_traffic_categories": ["fast_food", "convenience", "retail"],
    },
}

_DEFAULT_TEMPLATE = INDUSTRY_TEMPLATES["coffee"]


def _get_template(industry_template: str) -> Dict[str, Any]:
    return INDUSTRY_TEMPLATES.get(industry_template, _DEFAULT_TEMPLATE)


# ─── Main Scoring Function ────────────────────────────────────────────────────

def compute_score(
    competitor_summary: Dict[str, int],
    market_summary: Dict[str, Any],
    radius_m: float,
    industry_template: str,
) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Compute a 0–100 site score and return a list of 5 driver dicts:
      { name: str, impact: float, reason: str }
    """
    tmpl = _get_template(industry_template)
    competitor_cat = tmpl["competitor_category"]
    complementary = set(tmpl["complementary_categories"])
    foot_traffic_cats = set(tmpl["foot_traffic_categories"])

    competitor_count = competitor_summary.get(competitor_cat, 0)
    total_pois = market_summary.get("total_pois_in_radius", 0)
    poi_density = market_summary.get("poi_density_per_km2", 0.0)
    foot_traffic_count = market_summary.get("foot_traffic_indicators", 0)

    drivers: List[Dict[str, Any]] = []

    # ── Driver 1: Competitor Pressure (max 20) ──────────────────────────
    if competitor_count == 0:
        comp_score = 20.0
        comp_reason = (
            f"No direct {competitor_cat} competitors within {radius_m:.0f}m — "
            "strong first-mover advantage in this trade area."
        )
    elif competitor_count <= 2:
        comp_score = 14.0
        comp_reason = (
            f"Only {competitor_count} {competitor_cat} competitor(s) nearby — "
            "manageable competitive density; differentiation should secure share."
        )
    elif competitor_count <= 5:
        comp_score = 8.0
        comp_reason = (
            f"{competitor_count} competitors present — moderate saturation; "
            "a strong brand and execution edge will be required."
        )
    else:
        comp_score = max(0.0, 20.0 - competitor_count * 2.0)
        comp_reason = (
            f"High competitive saturation ({competitor_count} {competitor_cat} locations) — "
            "market may be crowded; validate true capture-rate assumptions."
        )

    drivers.append({"name": "Competitor Pressure", "impact": round(comp_score, 1), "reason": comp_reason})

    # ── Driver 2: Category Mix (max 20) ────────────────────────────────
    present = [c for c in complementary if competitor_summary.get(c, 0) > 0]
    mix_score = min(20.0, len(present) * 5.0)

    if mix_score >= 15:
        mix_reason = (
            f"Rich co-tenancy mix — {', '.join(present[:3])} present, "
            "creating natural cross-visit opportunities."
        )
    elif mix_score >= 5:
        mix_reason = (
            f"Moderate category variety ({', '.join(present)}) — "
            "some complementary draw exists but limited."
        )
    else:
        mix_reason = (
            "Limited complementary retail detected — "
            "verify independent foot-traffic sources before committing."
        )

    drivers.append({"name": "Category Mix", "impact": round(mix_score, 1), "reason": mix_reason})

    # ── Driver 3: Market Density (max 25) ──────────────────────────────
    if poi_density >= 20:
        density_score = 25.0
        density_reason = (
            f"Dense urban corridor ({poi_density:.1f} POIs/km²) — "
            "high ambient foot traffic environment."
        )
    elif poi_density >= 10:
        density_score = 18.0
        density_reason = (
            f"Active commercial area ({poi_density:.1f} POIs/km²) — "
            "solid baseline market activity."
        )
    elif poi_density >= 5:
        density_score = 12.0
        density_reason = (
            f"Moderate density ({poi_density:.1f} POIs/km²) — "
            "emerging or suburban market; growth potential with lower land cost."
        )
    else:
        density_score = max(0.0, poi_density * 2.0)
        density_reason = (
            f"Low commercial density ({poi_density:.1f} POIs/km²) — "
            "limited existing activity; site may rely on destination traffic."
        )

    drivers.append({"name": "Market Density", "impact": round(density_score, 1), "reason": density_reason})

    # ── Driver 4: Foot Traffic Potential (max 20) ───────────────────────
    if foot_traffic_count >= 8:
        ft_score = 20.0
        ft_reason = (
            f"{foot_traffic_count} foot-traffic anchors (grocery, fast food, etc.) — "
            "excellent ambient pedestrian draw."
        )
    elif foot_traffic_count >= 4:
        ft_score = 13.0
        ft_reason = (
            f"{foot_traffic_count} traffic anchors nearby — "
            "good pedestrian circulation expected."
        )
    elif foot_traffic_count >= 1:
        ft_score = 7.0
        ft_reason = (
            f"Some traffic anchors present ({foot_traffic_count}) — "
            "moderate pedestrian opportunity."
        )
    else:
        ft_score = 0.0
        ft_reason = (
            "Minimal foot-traffic anchors detected — "
            "location will need to build its own destination pull."
        )

    drivers.append({"name": "Foot Traffic Potential", "impact": round(ft_score, 1), "reason": ft_reason})

    # ── Driver 5: Brand Gap (max 15) ───────────────────────────────────
    saturation = (competitor_count / total_pois) if total_pois > 0 else 0.0

    if saturation < 0.05:
        gap_score = 15.0
        gap_reason = (
            f"Category significantly underrepresented ({competitor_count} of {total_pois} POIs) — "
            "clear white-space opportunity."
        )
    elif saturation < 0.15:
        gap_score = 8.0
        gap_reason = (
            f"Category moderately present (saturation {saturation:.0%}) — "
            "room to capture share with a strong brand."
        )
    else:
        gap_score = 2.0
        gap_reason = (
            f"Category well-represented locally (saturation {saturation:.0%}) — "
            "brand differentiation will be critical to compete."
        )

    drivers.append({"name": "Brand Gap", "impact": round(gap_score, 1), "reason": gap_reason})

    # ── Aggregate ───────────────────────────────────────────────────────
    total = sum(d["impact"] for d in drivers)
    total = round(max(0.0, min(100.0, total)), 1)

    logger.info(
        "Score=%s | %s",
        total,
        " | ".join(f"{d['name']}:{d['impact']}" for d in drivers),
    )
    return total, drivers
