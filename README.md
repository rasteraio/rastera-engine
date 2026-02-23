# rastera-engine

Production backend for the **Rastera** generic demo platform.
Provides geospatial site scoring, AI narrative generation, PDF reports, and portfolio ranking via a FastAPI REST API backed by PostGIS.

The Vercel frontend (rastera.io) calls this backend at **https://api.rastera.io**.
OpenAI calls are made server-side only — the API key never reaches the browser.

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│  Browser / Next.js Vercel App (rastera.io)                 │
│  • Server-side fetch → RASTERA_API_BASE env var            │
│  • NO direct OpenAI or DB access                           │
└───────────────────────┬────────────────────────────────────┘
                        │  HTTPS  (api.rastera.io)
                ┌───────▼────────────────────────┐
                │  Caddy  (TLS termination)       │
                │  Reverse proxy → :8080          │
                └───────┬────────────────────────┘
                        │ internal Docker network
         ┌──────────────┼──────────────┐
         │              │              │
  ┌──────▼──────┐ ┌─────▼──────┐ ┌───▼────────┐
  │  api        │ │  db         │ │  worker    │
  │  FastAPI    │ │  Postgres16 │ │  APScheduler│
  │  :8080      │ │  + PostGIS  │ │  (cron)    │
  └─────────────┘ └────────────┘ └────────────┘
         │                ↑
         └────────────────┘
         SQLAlchemy async (psycopg3)
```

---

## Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI 0.110+ (Python 3.11) |
| Database | PostgreSQL 16 + PostGIS 3.4 |
| ORM | SQLAlchemy 2.0 async + GeoAlchemy2 |
| DB driver | psycopg3 (async-native) |
| AI | OpenAI SDK (server-side; gpt-4.1-mini default) |
| PDF | WeasyPrint → HTML template |
| Geocoding | Nominatim (pluggable adapter) |
| Reverse proxy | Caddy (auto TLS via Let's Encrypt) |
| Containerisation | Docker + docker compose plugin |
| Background jobs | APScheduler (in worker container) |
| Rate limiting | slowapi (in-memory V1; Redis hook in V2) |

---

## Repository Structure

```
rastera-engine/
├── app/
│   ├── main.py              # FastAPI app + all endpoints
│   ├── settings.py          # Pydantic settings (env vars)
│   ├── db.py                # Async SQLAlchemy engine
│   ├── models.py            # ORM models (Tenant, Site, POI, Score)
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── sql/
│   │   ├── schema.sql       # PostGIS DDL (auto-run on first start)
│   │   └── seed_demo.sql    # Demo tenant + 5 sites + 52 POIs (Chicago)
│   ├── services/
│   │   ├── geocode.py       # Pluggable geocoder (Nominatim default)
│   │   ├── geo.py           # Trade area polygon + PostGIS queries
│   │   ├── scoring.py       # V1 weighted scoring model
│   │   ├── ai.py            # OpenAI narrative generation
│   │   └── report.py        # WeasyPrint PDF generation
│   └── utils/
│       └── logging.py       # Structured logging
├── templates/
│   └── report.html          # PDF report HTML template
├── worker/
│   └── worker.py            # APScheduler background jobs
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in real values:

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | **Yes** | — | OpenAI secret key (never exposed to browser) |
| `OPENAI_MODEL` | No | `gpt-4.1-mini` | Model name |
| `AI_ENABLED` | No | `true` | Set `false` to disable AI calls entirely |
| `DATABASE_URL` | No | `postgresql+psycopg://rastera:CHANGE_ME@db:5432/rastera` | Async SQLAlchemy DSN |
| `DB_PASSWORD` | **Yes** | `CHANGE_ME` | Postgres password (used by docker-compose) |
| `ALLOWED_ORIGINS` | **Yes** | `https://rastera.io,...` | Comma-separated CORS origins |
| `APP_ENV` | No | `production` | Environment label |
| `LOG_LEVEL` | No | `INFO` | `DEBUG` / `INFO` / `WARNING` |

---

## Local Development

### Prerequisites
- Docker Desktop (or Docker Engine + compose plugin)
- Git

### Start everything

```bash
git clone https://github.com/your-org/rastera-engine.git
cd rastera-engine

# Create local .env (AI calls are optional for local dev)
cp .env.example .env
# Edit .env — at minimum set DB_PASSWORD and ALLOWED_ORIGINS

docker compose up --build
```

On first start, docker-compose will:
1. Pull `postgis/postgis:16-3.4`
2. Run `schema.sql` then `seed_demo.sql` automatically
3. Start the API on **http://localhost:8080**

### Verify

```bash
curl http://localhost:8080/health
# → {"status":"ok","version":"1.0.0"}

curl http://localhost:8080/health/db
# → {"status":"ok","db":"connected"}
```

### Local dev with port-forwarded DB (optional)

Uncomment the `db.ports` block in `docker-compose.yml`:
```yaml
ports:
  - "127.0.0.1:5432:5432"
```
Then connect with: `psql postgresql://rastera:CHANGE_ME@localhost:5432/rastera`

---

## Production Deployment (VPS)

### 1. Provision a VPS

- **Recommended**: Ubuntu 22.04 LTS, 2 vCPU, 4 GB RAM minimum
- Point DNS: `api.rastera.io` → VPS public IP

### 2. Install Docker

```bash
# As root or sudo user
curl -fsSL https://get.docker.com | sh
usermod -aG docker $USER
newgrp docker
docker compose version   # verify plugin installed
```

### 3. Clone the repo

```bash
cd /opt
git clone https://github.com/your-org/rastera-engine.git
cd rastera-engine
```

### 4. Create production `.env`

```bash
cp .env.example .env
nano .env
```

Fill in:
```env
OPENAI_API_KEY=sk-...your-key...
OPENAI_MODEL=gpt-4.1-mini
AI_ENABLED=true

DB_PASSWORD=a-long-random-password-here
DATABASE_URL=postgresql+psycopg://rastera:a-long-random-password-here@db:5432/rastera

ALLOWED_ORIGINS=https://rastera.io,https://www.rastera.io,https://your-app.vercel.app

APP_ENV=production
LOG_LEVEL=INFO
```

### 5. Start services

```bash
docker compose up -d --build

# Watch logs
docker compose logs -f api
docker compose logs -f db
```

### 6. Install Caddy (reverse proxy + auto HTTPS)

```bash
apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  | tee /etc/apt/sources.list.d/caddy-stable.list
apt update && apt install caddy
```

### 7. Configure Caddy

Edit `/etc/caddy/Caddyfile`:

```
api.rastera.io {
    reverse_proxy localhost:8080

    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        -Server
    }

    # Optional: basic access logging
    log {
        output file /var/log/caddy/api.rastera.io.log {
            roll_size 10mb
            roll_keep 5
        }
    }
}
```

```bash
systemctl enable caddy
systemctl restart caddy
systemctl status caddy
```

Caddy will automatically obtain and renew a Let's Encrypt certificate for `api.rastera.io`.

### 8. Verify production

```bash
curl https://api.rastera.io/health
# → {"status":"ok","version":"1.0.0"}

curl https://api.rastera.io/health/db
# → {"status":"ok","db":"connected"}
```

---

## API Reference

All endpoints return JSON unless noted. Base URL: `https://api.rastera.io`

### `GET /health`
Liveness probe. No DB required.
```json
{"status": "ok", "version": "1.0.0"}
```

### `GET /health/db`
Readiness probe. Confirms DB connectivity.

---

### `POST /v1/site/analyze`
Run the full scoring pipeline for a location.

**Request body:**
```json
{
  "tenant_slug": "demo-coffee",
  "address": "100 W Adams St, Chicago, IL",
  "radius_m": 1600,
  "industry_template": "coffee",
  "generate_ai_summary": true
}
```
Or with explicit coordinates:
```json
{
  "tenant_slug": "demo-coffee",
  "lat": 41.8827,
  "lon": -87.6233,
  "radius_m": 1600,
  "industry_template": "coffee"
}
```

**Response:**
```json
{
  "site_id": "uuid",
  "normalized_lat": 41.8827,
  "normalized_lon": -87.6233,
  "trade_area_geojson": { "type": "Feature", "geometry": {...}, "properties": {...} },
  "competitor_summary": { "coffee": 3, "bakery": 2, "fast_food": 3 },
  "market_summary": {
    "total_pois_in_radius": 12,
    "poi_density_per_km2": 23.5,
    "foot_traffic_indicators": 7,
    "market_activity_score": 89
  },
  "score": {
    "total": 72.5,
    "drivers": [
      { "name": "Competitor Pressure", "impact": 8.0, "reason": "..." },
      ...
    ]
  },
  "ai_summary": {
    "executive_summary": "...",
    "opportunities": ["..."],
    "risks": ["..."],
    "next_actions": ["..."]
  }
}
```

---

### `POST /v1/site/ai-summary`
(Re-)generate an AI narrative for an existing site or from raw data.

**Option A — by site_id:**
```json
{ "site_id": "uuid" }
```

**Option B — inline data:**
```json
{
  "score": 72.5,
  "competitor_summary": { "coffee": 3, "fast_food": 3 },
  "market_summary": { "total_pois_in_radius": 12, "poi_density_per_km2": 23.5 },
  "address": "100 W Adams St, Chicago, IL",
  "radius_m": 1600,
  "industry_template": "coffee"
}
```

**Response:**
```json
{
  "executive_summary": "...",
  "opportunities": ["..."],
  "risks": ["..."],
  "next_actions": ["..."]
}
```

---

### `POST /v1/site/report/pdf`
Download a PDF site report.

**Request body:**
```json
{ "site_id": "uuid" }
```

**Response:** `application/pdf` stream — browser will download the file.

---

### `GET /v1/portfolio/rank`
Rank candidate sites by score.

**Query params:**
- `tenant_slug` (required)
- `industry_template` (default: `coffee`)
- `limit` (default: 10, max: 50)

**Example:**
```
GET /v1/portfolio/rank?tenant_slug=demo-coffee&industry_template=coffee&limit=5
```

**Response:**
```json
{
  "tenant_slug": "demo-coffee",
  "industry_template": "coffee",
  "sites": [
    {
      "site_id": "uuid",
      "name": "Store 2 — River North",
      "address": "540 N Michigan Ave, Chicago, IL",
      "lat": 41.8918,
      "lon": -87.6318,
      "score": 81.0,
      "rank": 1
    },
    ...
  ]
}
```

---

## Testing with curl

Run these against `http://localhost:8080` (local) or `https://api.rastera.io` (production):

```bash
BASE=http://localhost:8080

# 1. Health
curl -s $BASE/health | jq .

# 2. Analyze a site by address
curl -s -X POST $BASE/v1/site/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_slug": "demo-coffee",
    "address": "100 W Adams St, Chicago, IL",
    "radius_m": 1600,
    "industry_template": "coffee",
    "generate_ai_summary": false
  }' | jq '{site_id, score: .score.total}'

# 3. Analyze by coordinates (faster — skips geocoding)
SITE_ID=$(curl -s -X POST $BASE/v1/site/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_slug": "demo-coffee",
    "lat": 41.8827, "lon": -87.6233,
    "radius_m": 1600,
    "industry_template": "coffee",
    "generate_ai_summary": false
  }' | jq -r .site_id)
echo "site_id: $SITE_ID"

# 4. Generate AI summary for that site
curl -s -X POST $BASE/v1/site/ai-summary \
  -H "Content-Type: application/json" \
  -d "{\"site_id\": \"$SITE_ID\"}" | jq .

# 5. Download PDF report
curl -s -X POST $BASE/v1/site/report/pdf \
  -H "Content-Type: application/json" \
  -d "{\"site_id\": \"$SITE_ID\"}" \
  -o report.pdf && echo "PDF saved as report.pdf"

# 6. Portfolio ranking
curl -s "$BASE/v1/portfolio/rank?tenant_slug=demo-coffee&industry_template=coffee" | jq .

# 7. Interactive API docs (browser)
open $BASE/docs
```

---

## Vercel Integration

### Set environment variable in Vercel

In your Vercel project settings → Environment Variables:

```
RASTERA_API_BASE = https://api.rastera.io
```

### Next.js server-side fetch (App Router)

```typescript
// app/api/analyze/route.ts  — server-side only, key never in browser
import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.RASTERA_API_BASE!; // set in Vercel env vars

export async function POST(req: NextRequest) {
  const body = await req.json();

  const res = await fetch(`${API_BASE}/v1/site/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      tenant_slug: body.tenant_slug ?? "demo-coffee",
      lat: body.lat,
      lon: body.lon,
      address: body.address,
      radius_m: body.radius_m ?? 1600,
      industry_template: body.industry_template ?? "coffee",
      generate_ai_summary: true,
    }),
    // Optional: cache for 60s during heavy demo traffic
    next: { revalidate: 60 },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    return NextResponse.json(err, { status: res.status });
  }

  return NextResponse.json(await res.json());
}
```

```typescript
// app/api/portfolio/route.ts
import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.RASTERA_API_BASE!;

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const tenantSlug = searchParams.get("tenant_slug") ?? "demo-coffee";
  const template = searchParams.get("industry_template") ?? "coffee";

  const res = await fetch(
    `${API_BASE}/v1/portfolio/rank?tenant_slug=${tenantSlug}&industry_template=${template}`,
    { next: { revalidate: 300 } }
  );

  return NextResponse.json(await res.json(), { status: res.status });
}
```

```typescript
// app/api/report/[siteId]/route.ts — stream PDF to browser
import { NextRequest } from "next/server";

const API_BASE = process.env.RASTERA_API_BASE!;

export async function GET(
  _req: NextRequest,
  { params }: { params: { siteId: string } }
) {
  const res = await fetch(`${API_BASE}/v1/site/report/pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ site_id: params.siteId }),
  });

  const pdf = await res.arrayBuffer();
  return new Response(pdf, {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `attachment; filename="rastera-report.pdf"`,
    },
  });
}
```

---

## Scoring Model (V1)

Five weighted drivers → composite 0–100 score:

| Driver | Max pts | Signal |
|---|---|---|
| Competitor Pressure | 20 | Fewer direct competitors = higher |
| Category Mix | 20 | Complementary categories present |
| Market Density | 25 | POI density per km² |
| Foot Traffic Potential | 20 | Adjacent grocery, fast food, convenience |
| Brand Gap | 15 | Underrepresented category = opportunity |

All drivers are interpretable and returned in the API response. The scoring model lives in `app/services/scoring.py` — weights are easy to tune per client.

---

## Geocoding

Default: **OpenStreetMap Nominatim** (free, no API key required).

To swap providers, implement `GeocoderAdapter` in `app/services/geocode.py` and call `set_geocoder(YourGeocoder())` at startup:

```python
# Example in app/main.py startup event
from app.services.geocode import set_geocoder
from app.services.geocode import GoogleGeocoder  # your adapter

@app.on_event("startup")
async def startup():
    set_geocoder(GoogleGeocoder(api_key=settings.GOOGLE_MAPS_KEY))
```

---

## Roadmap / TODOs

| Area | Status | Notes |
|---|---|---|
| Drive-time trade areas | TODO | Replace radius buffer with Valhalla/OSRM isochrones |
| Real demographics | TODO | Census ACS, Esri Demographics, SafeGraph |
| Multi-tenant auth | TODO | API key / JWT per tenant; rate limit per key |
| Redis rate limiting | TODO | Replace in-memory slowapi with Redis backend |
| Real-time POI refresh | TODO | OSM Overpass, Google Places pipeline |
| Alembic migrations | TODO | Add for schema versioning beyond initial deploy |
| Weekly report delivery | TODO | Complete worker job + S3 + email |
| Drive-time geocoder adapters | TODO | Google Maps, HERE, Esri adapters in geocode.py |
| Celery task queue | TODO | For distributed async jobs in production |

---

## Security Notes

- **OpenAI key is VPS-only**: stored in `.env`, injected into `api` and `worker` containers, never returned by any endpoint.
- **Database not publicly exposed**: `db` service has no host port mapping in production. Only `api` and `worker` (on the internal `rastera_net` bridge) can reach it.
- **CORS**: controlled via `ALLOWED_ORIGINS` env var. Add your Vercel preview URLs as needed.
- **Rate limiting**: V1 uses in-memory slowapi limits (20 req/min for analyze, 5 req/min for PDF). Swap to Redis for multi-worker deployments.
- **HTTPS**: enforced by Caddy with automatic Let's Encrypt renewal.

---

## Updating in Production

```bash
cd /opt/rastera-engine
git pull
docker compose up -d --build api worker
# DB container is not rebuilt unless schema changes require it
docker compose logs -f api
```

---

*Rastera Engine v1.0 — built for speed-to-demo, designed to scale.*
