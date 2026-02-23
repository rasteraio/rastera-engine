"""
Rastera Engine — Pydantic Request / Response Schemas
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ─── Site Analysis ────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    address: Optional[str] = Field(None, description="Street address to geocode")
    lat: Optional[float] = Field(None, ge=-90, le=90, description="Latitude (WGS84)")
    lon: Optional[float] = Field(None, ge=-180, le=180, description="Longitude (WGS84)")
    radius_m: int = Field(default=1600, ge=100, le=50000, description="Trade area radius in metres")
    industry_template: str = Field(default="coffee", description="Industry scoring template")
    generate_ai_summary: bool = Field(default=True, description="Call OpenAI to produce narrative")


class ScoreDriver(BaseModel):
    name: str
    impact: float  # contribution to total (positive = helps, negative = hurts)
    reason: str


class ScoreResult(BaseModel):
    total: float = Field(..., ge=0, le=100)
    drivers: List[ScoreDriver]


class AISummaryData(BaseModel):
    executive_summary: str
    opportunities: List[str]
    risks: List[str]
    next_actions: List[str]


class AnalyzeResponse(BaseModel):
    site_id: str
    normalized_lat: float
    normalized_lon: float
    trade_area_geojson: Dict[str, Any]
    competitor_summary: Dict[str, int]
    market_summary: Dict[str, Any]
    score: ScoreResult
    ai_summary: Optional[AISummaryData] = None


# ─── AI Summary ───────────────────────────────────────────────────────────────

class AISummaryRequest(BaseModel):
    # Option A: look up an existing site
    site_id: Optional[str] = None
    # Option B: pass raw data directly
    score: Optional[float] = Field(None, ge=0, le=100)
    competitor_summary: Optional[Dict[str, int]] = None
    market_summary: Optional[Dict[str, Any]] = None
    address: Optional[str] = None
    radius_m: Optional[int] = 1600
    industry_template: Optional[str] = "coffee"


class AISummaryResponse(BaseModel):
    executive_summary: str
    opportunities: List[str]
    risks: List[str]
    next_actions: List[str]


# ─── Portfolio ────────────────────────────────────────────────────────────────

class RankedSite(BaseModel):
    site_id: str
    name: str
    address: Optional[str]
    lat: float
    lon: float
    score: float
    rank: int


class PortfolioRankResponse(BaseModel):
    tenant_slug: str
    industry_template: str
    sites: List[RankedSite]
