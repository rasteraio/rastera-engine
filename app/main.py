"""
Rastera Engine — FastAPI Application Entry Point
All V1 endpoints defined here.  Split into routers in V2 if this file grows.
"""
import hashlib
import io
import uuid
from datetime import datetime
from typing import Any, Dict

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import APIKeyHeader
from geoalchemy2 import WKTElement
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models import Score, Site, Tenant, TenantApiKey
from app.schemas import (
    AISummaryRequest,
    AISummaryResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    PortfolioRankResponse,
    RankedSite,
    ScoreDriver,
    ScoreResult,
)
from app.services.ai import generate_site_summary
from app.services.geo import (
    compute_market_summary,
    compute_trade_area_geojson,
    get_pois_in_radius,
    summarize_competitors,
)
from app.services.geocode import get_geocoder
from app.services.report import generate_pdf_report
from app.services.scoring import compute_score
from app.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# ─── Rate Limiter ─────────────────────────────────────────────────────────────
# V1: in-memory (single-process).
# TODO: swap storage_uri to Redis ("redis://redis:6379") for multi-worker scale-out.
limiter = Limiter(key_func=get_remote_address)

# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Rastera Engine",
    version="1.0.0",
    description=(
        "Geospatial site selection, AI narrative, and PDF reporting backend "
        "for the Rastera demo platform."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ─── Auth ─────────────────────────────────────────────────────────────────────

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


async def get_current_tenant(
    raw_key: str = Security(_api_key_header),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """
    Validate the X-API-Key header and return the associated Tenant.
    Raises 401 if the key is missing, unknown, or revoked.
    """
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    result = await db.execute(
        select(TenantApiKey)
        .where(TenantApiKey.key_hash == key_hash)
        .where(TenantApiKey.revoked_at.is_(None))
        .options(selectinload(TenantApiKey.tenant))
    )
    rec = result.scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    rec.last_used_at = datetime.utcnow()
    await db.commit()
    return rec.tenant


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"])
async def health():
    """Lightweight liveness probe — no DB required."""
    return {"status": "ok", "version": "1.0.0"}


@app.get("/health/db", tags=["ops"])
async def health_db(db: AsyncSession = Depends(get_db)):
    """Readiness probe — confirms DB connectivity."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as exc:
        logger.error("DB health check failed: %s", exc)
        raise HTTPException(status_code=503, detail="Database unavailable")


# ─── Site Analysis ────────────────────────────────────────────────────────────

@app.post("/v1/site/analyze", response_model=AnalyzeResponse, tags=["site"])
@limiter.limit("20/minute")
async def analyze_site(
    request: Request,
    body: AnalyzeRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> AnalyzeResponse:
    """
    Core endpoint.  Accepts a location (address or lat/lon), runs the full
    scoring pipeline, optionally calls OpenAI, persists results, and returns
    the complete analysis JSON.
    """
    # 1. Resolve coordinates
    lat, lon = await _resolve_coordinates(body)

    # 2. Persist site record
    site_id = str(uuid.uuid4())
    site_name = body.address or f"Site @ {lat:.4f}, {lon:.4f}"
    site = Site(
        id=site_id,
        tenant_id=tenant.id,
        name=site_name,
        address=body.address,
        geom=WKTElement(f"POINT({lon} {lat})", srid=4326),
    )
    db.add(site)
    await db.flush()   # write site so FK constraint satisfied for score

    # 3. Trade area polygon
    trade_area = compute_trade_area_geojson(lat, lon, body.radius_m)

    # 4. Query POIs
    pois = await get_pois_in_radius(db, lat, lon, body.radius_m, tenant.id)

    # 5. Summaries
    competitor_summary = summarize_competitors(pois, body.industry_template)
    market_summary = compute_market_summary(pois, lat, lon, body.radius_m)

    # 6. Score
    score_total, drivers = compute_score(
        competitor_summary, market_summary, body.radius_m, body.industry_template
    )

    # 7. AI summary (server-side; key never exposed to browser)
    ai_data: Dict[str, Any] | None = None
    if body.generate_ai_summary:
        ai_data = await generate_site_summary(
            score=score_total,
            drivers=drivers,
            competitor_summary=competitor_summary,
            market_summary=market_summary,
            address=body.address,
            radius_m=body.radius_m,
            industry_template=body.industry_template,
        )

    # 8. Persist score
    score_record = Score(
        id=str(uuid.uuid4()),
        site_id=site_id,
        score_total=score_total,
        drivers_json=drivers,
        competitor_summary=competitor_summary,
        market_summary=market_summary,
        ai_summary=ai_data,
        radius_m=body.radius_m,
        industry_template=body.industry_template,
    )
    db.add(score_record)
    await db.commit()

    logger.info(
        "analyze_site: site_id=%s score=%.1f tenant=%s",
        site_id, score_total, tenant.slug,
    )

    return AnalyzeResponse(
        site_id=site_id,
        normalized_lat=lat,
        normalized_lon=lon,
        trade_area_geojson=trade_area,
        competitor_summary=competitor_summary,
        market_summary=market_summary,
        score=ScoreResult(
            total=score_total,
            drivers=[ScoreDriver(**d) for d in drivers],
        ),
        ai_summary=ai_data,
    )


# ─── AI Summary ───────────────────────────────────────────────────────────────

@app.post("/v1/site/ai-summary", response_model=AISummaryResponse, tags=["site"])
@limiter.limit("10/minute")
async def ai_summary(
    request: Request,
    body: AISummaryRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> AISummaryResponse:
    """
    (Re-)generate an AI narrative.
    Option A: pass site_id — looks up latest stored score (scoped to caller's tenant).
    Option B: pass score + competitor_summary + market_summary inline.
    """
    if body.site_id:
        result = await db.execute(
            select(Score, Site)
            .join(Site, Score.site_id == Site.id)
            .where(Score.site_id == body.site_id)
            .where(Site.tenant_id == tenant.id)
            .order_by(Score.created_at.desc())
            .limit(1)
        )
        row = result.first()
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"No analysis found for site_id={body.site_id!r}",
            )
        score_rec, site = row
        ai_data = await generate_site_summary(
            score=float(score_rec.score_total),
            drivers=score_rec.drivers_json or [],
            competitor_summary=score_rec.competitor_summary or {},
            market_summary=score_rec.market_summary or {},
            address=site.address,
            radius_m=score_rec.radius_m,
            industry_template=score_rec.industry_template,
        )
    else:
        if body.score is None or body.competitor_summary is None:
            raise HTTPException(
                status_code=422,
                detail="Provide either site_id or (score + competitor_summary + market_summary).",
            )
        ai_data = await generate_site_summary(
            score=body.score,
            drivers=[],
            competitor_summary=body.competitor_summary,
            market_summary=body.market_summary or {},
            address=body.address,
            radius_m=body.radius_m or 1600,
            industry_template=body.industry_template or "coffee",
        )

    return AISummaryResponse(**ai_data)


# ─── PDF Report ───────────────────────────────────────────────────────────────

@app.post("/v1/site/report/pdf", tags=["site"])
@limiter.limit("5/minute")
async def generate_report(
    request: Request,
    body: Dict[str, Any],
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Generate and stream a PDF site report for an existing site_id."""
    site_id: str | None = body.get("site_id")
    if not site_id:
        raise HTTPException(status_code=422, detail="site_id is required")

    result = await db.execute(
        select(Score, Site)
        .join(Site, Score.site_id == Site.id)
        .where(Score.site_id == site_id)
        .where(Site.tenant_id == tenant.id)
        .order_by(Score.created_at.desc())
        .limit(1)
    )
    row = result.first()
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"No analysis found for site_id={site_id!r}",
        )
    score_rec, site = row

    # Fetch centroid coordinates from PostGIS
    geom_result = await db.execute(
        text(
            "SELECT ST_Y(geom::geometry) AS lat, ST_X(geom::geometry) AS lon "
            "FROM sites WHERE id = :id"
        ),
        {"id": site_id},
    )
    geom_row = geom_result.first()
    lat = geom_row.lat if geom_row else 0.0
    lon = geom_row.lon if geom_row else 0.0

    pdf_bytes = generate_pdf_report(
        site_id=site.id,
        site_name=site.name,
        address=site.address,
        lat=lat,
        lon=lon,
        score=float(score_rec.score_total),
        drivers=score_rec.drivers_json or [],
        competitor_summary=score_rec.competitor_summary or {},
        market_summary=score_rec.market_summary or {},
        ai_summary=score_rec.ai_summary,
        radius_m=score_rec.radius_m,
        industry_template=score_rec.industry_template,
    )

    filename = f"rastera-report-{site_id[:8]}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── Portfolio Ranking ────────────────────────────────────────────────────────

@app.get("/v1/portfolio/rank", response_model=PortfolioRankResponse, tags=["portfolio"])
@limiter.limit("30/minute")
async def rank_portfolio(
    request: Request,
    industry_template: str = "coffee",
    limit: int = 10,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> PortfolioRankResponse:
    """
    Return the top-N candidate sites for the authenticated tenant, ranked by
    their latest score for the given industry_template.
    """
    sql = text("""
        SELECT
            s.id           AS site_id,
            s.name,
            s.address,
            ST_Y(s.geom::geometry) AS lat,
            ST_X(s.geom::geometry) AS lon,
            sc.score_total,
            ROW_NUMBER() OVER (ORDER BY sc.score_total DESC) AS rank
        FROM sites s
        JOIN LATERAL (
            SELECT score_total
            FROM scores
            WHERE site_id = s.id
              AND industry_template = :industry_template
            ORDER BY created_at DESC
            LIMIT 1
        ) sc ON true
        WHERE s.tenant_id = :tenant_id
        ORDER BY sc.score_total DESC
        LIMIT :lim
    """)

    result = await db.execute(
        sql,
        {
            "tenant_id": tenant.id,
            "industry_template": industry_template,
            "lim": min(limit, 50),
        },
    )
    rows = result.fetchall()

    sites = [
        RankedSite(
            site_id=str(r.site_id),
            name=r.name,
            address=r.address,
            lat=r.lat,
            lon=r.lon,
            score=float(r.score_total),
            rank=r.rank,
        )
        for r in rows
    ]

    return PortfolioRankResponse(
        tenant_slug=tenant.slug,
        industry_template=industry_template,
        sites=sites,
    )


# ─── Private helpers ──────────────────────────────────────────────────────────

async def _resolve_coordinates(body: AnalyzeRequest):
    """Return (lat, lon) from lat/lon fields or by geocoding address."""
    if body.lat is not None and body.lon is not None:
        return body.lat, body.lon

    if body.address:
        geocoder = get_geocoder()
        coords = await geocoder.geocode(body.address)
        if coords is None:
            raise HTTPException(
                status_code=422,
                detail=f"Could not geocode address: {body.address!r}",
            )
        return coords

    raise HTTPException(
        status_code=422,
        detail="Provide either (lat + lon) or an address string.",
    )
