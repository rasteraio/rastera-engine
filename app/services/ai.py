"""
Rastera Engine — OpenAI AI Summary Service
Server-side only. The API key never leaves this container.

Safety:
  - If AI_ENABLED=false or OPENAI_API_KEY is blank → graceful fallback.
  - If the OpenAI call fails (timeout, quota, etc.) → graceful fallback.
  - Uses response_format=json_object to guarantee parsable output.
  - Validates all expected keys before returning.
"""
import json
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from app.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# ─── Fallback returned when AI is unavailable ─────────────────────────────────
FALLBACK_SUMMARY: Dict[str, Any] = {
    "executive_summary": (
        "AI narrative is temporarily unavailable. "
        "Please review the quantitative score and driver breakdown for site insights."
    ),
    "opportunities": [
        "Review the competitor summary for market-gap opportunities.",
        "Assess adjacent foot-traffic generators for complementary draw.",
    ],
    "risks": [
        "Validate foot-traffic assumptions with on-site observation.",
        "Confirm competitor counts with primary research.",
    ],
    "next_actions": [
        "Request a full AI analysis once service is restored.",
        "Schedule a site visit to validate quantitative findings.",
    ],
}

_REQUIRED_KEYS = ("executive_summary", "opportunities", "risks", "next_actions")

# Module-level client (lazy-initialised)
_client: Optional[AsyncOpenAI] = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


# ─── Main entry point ─────────────────────────────────────────────────────────

async def generate_site_summary(
    score: float,
    drivers: List[Dict[str, Any]],
    competitor_summary: Dict[str, int],
    market_summary: Dict[str, Any],
    address: Optional[str],
    radius_m: int,
    industry_template: str,
) -> Dict[str, Any]:
    """
    Call OpenAI to produce a structured JSON narrative grounded in site metrics.
    Returns a dict with keys: executive_summary, opportunities, risks, next_actions.
    """
    if not settings.AI_ENABLED:
        logger.info("AI disabled (AI_ENABLED=false) — returning fallback")
        return FALLBACK_SUMMARY

    if not settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set — returning fallback")
        return FALLBACK_SUMMARY

    drivers_text = "\n".join(
        f"  • {d['name']}: {d['impact']:+.1f} pts — {d['reason']}"
        for d in drivers
    )
    competitor_text = (
        ", ".join(f"{v} {k}" for k, v in competitor_summary.items())
        or "no POIs detected"
    )

    prompt = f"""You are a senior commercial real estate and retail site selection analyst. \
Produce a data-driven JSON report for the site described below.

SITE DATA
─────────
Industry template : {industry_template}
Trade area radius : {radius_m} m
Address / location: {address or "coordinates provided — no street address"}
Composite score   : {score:.1f} / 100

SCORE DRIVERS
─────────────
{drivers_text}

COMPETITIVE & POI LANDSCAPE (within {radius_m} m)
────────────────────────────────────────────────
{competitor_text}

MARKET CONTEXT
──────────────
Total POIs in trade area : {market_summary.get("total_pois_in_radius", "N/A")}
POI density              : {market_summary.get("poi_density_per_km2", "N/A")} per km²
Foot-traffic anchors     : {market_summary.get("foot_traffic_indicators", "N/A")}
Market activity score    : {market_summary.get("market_activity_score", "N/A")} / 100

INSTRUCTIONS
────────────
Return ONLY a valid JSON object with exactly these four keys:

  "executive_summary" — 2–3 sentences of strategic assessment grounded in the numbers above.
  "opportunities"     — list of 3–5 specific, data-backed opportunity statements.
  "risks"             — list of 2–4 specific, quantified risk statements.
  "next_actions"      — list of 3–5 concrete next steps for the site evaluation team.

Be specific. Quote the actual figures. Avoid generic boilerplate.
"""

    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a data-driven commercial site selection analyst. "
                        "Always respond with valid JSON only — no markdown, no extra text."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.35,
            max_tokens=1200,
        )

        content = response.choices[0].message.content or "{}"
        parsed: Dict[str, Any] = json.loads(content)

        # Ensure all required keys exist
        for key in _REQUIRED_KEYS:
            if key not in parsed:
                parsed[key] = FALLBACK_SUMMARY[key]

        logger.info("AI summary generated via model=%s", settings.OPENAI_MODEL)
        return parsed

    except Exception as exc:
        logger.error("OpenAI call failed: %s", exc)
        return FALLBACK_SUMMARY
