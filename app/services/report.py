"""
Rastera Engine — PDF Report Service
Renders templates/report.html via Jinja2 → WeasyPrint → PDF bytes.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from app.utils.logging import get_logger

logger = get_logger(__name__)

_jinja = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"]),
)


def _score_color(score: float) -> str:
    if score >= 70:
        return "#16a34a"   # green-600
    if score >= 45:
        return "#d97706"   # amber-600
    return "#dc2626"       # red-600


def _score_label(score: float) -> str:
    if score >= 70:
        return "Strong"
    if score >= 45:
        return "Moderate"
    return "Weak"


def generate_pdf_report(
    site_id: str,
    site_name: str,
    address: Optional[str],
    lat: float,
    lon: float,
    score: float,
    drivers: List[Dict[str, Any]],
    competitor_summary: Dict[str, int],
    market_summary: Dict[str, Any],
    ai_summary: Optional[Dict[str, Any]],
    radius_m: int,
    industry_template: str,
) -> bytes:
    """Return PDF as bytes for streaming download."""
    template = _jinja.get_template("report.html")

    html_str = template.render(
        site_id=site_id,
        site_name=site_name,
        address=address or f"{lat:.6f}, {lon:.6f}",
        lat=round(lat, 6),
        lon=round(lon, 6),
        score=score,
        score_color=_score_color(score),
        score_label=_score_label(score),
        drivers=drivers,
        competitor_summary=competitor_summary,
        market_summary=market_summary,
        ai_summary=ai_summary,
        radius_m=radius_m,
        industry_template=industry_template.replace("_", " ").title(),
        generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    )

    pdf_bytes: bytes = HTML(string=html_str, base_url=".").write_pdf()
    logger.info("PDF generated: site_id=%s size=%d bytes", site_id, len(pdf_bytes))
    return pdf_bytes
