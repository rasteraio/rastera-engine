-- ─── Rastera Engine — Demo Seed Data ─────────────────────────────────────────
-- Creates the "demo-coffee" tenant, 5 candidate sites, and 52 POIs across
-- Chicago neighbourhoods (Loop, River North, Lincoln Park, Wicker Park, Hyde Park).
-- Uses INSERT … ON CONFLICT DO NOTHING so re-running is idempotent.
-- Anonymised: no real brand names for the candidate sites.
-- ─────────────────────────────────────────────────────────────────────────────

DO $$
DECLARE
    v_tenant_id UUID;
BEGIN

-- ── Tenant ────────────────────────────────────────────────────────────────────
INSERT INTO tenants (id, name, slug)
VALUES (
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'Demo Coffee Brand',
    'demo-coffee'
)
ON CONFLICT (slug) DO NOTHING;

SELECT id INTO v_tenant_id FROM tenants WHERE slug = 'demo-coffee';

-- ── Candidate Sites ───────────────────────────────────────────────────────────
-- 5 anonymised locations in Chicago metro area.
INSERT INTO sites (id, tenant_id, name, address, geom) VALUES
(
    '11111111-0000-0000-0000-000000000001',
    v_tenant_id,
    'Store 1 — Loop',
    '100 W Adams St, Chicago, IL 60603',
    ST_SetSRID(ST_MakePoint(-87.6233, 41.8827), 4326)
),
(
    '11111111-0000-0000-0000-000000000002',
    v_tenant_id,
    'Store 2 — River North',
    '540 N Michigan Ave, Chicago, IL 60611',
    ST_SetSRID(ST_MakePoint(-87.6318, 41.8918), 4326)
),
(
    '11111111-0000-0000-0000-000000000003',
    v_tenant_id,
    'Store 3 — Lincoln Park',
    '2200 N Lincoln Ave, Chicago, IL 60614',
    ST_SetSRID(ST_MakePoint(-87.6484, 41.9242), 4326)
),
(
    '11111111-0000-0000-0000-000000000004',
    v_tenant_id,
    'Store 4 — Wicker Park',
    '1560 N Milwaukee Ave, Chicago, IL 60622',
    ST_SetSRID(ST_MakePoint(-87.6782, 41.9088), 4326)
),
(
    '11111111-0000-0000-0000-000000000005',
    v_tenant_id,
    'Store 5 — Hyde Park',
    '1500 E 55th St, Chicago, IL 60615',
    ST_SetSRID(ST_MakePoint(-87.5907, 41.7943), 4326)
)
ON CONFLICT (id) DO NOTHING;

-- ── Points of Interest — Loop area ────────────────────────────────────────────
INSERT INTO pois (tenant_id, name, category, brand, geom) VALUES

-- Coffee (direct competitors)
(v_tenant_id, 'Corner Brew Co.',         'coffee',    'Corner Brew',       ST_SetSRID(ST_MakePoint(-87.6245, 41.8821), 4326)),
(v_tenant_id, 'Metro Espresso Bar',      'coffee',    'Metro Espresso',    ST_SetSRID(ST_MakePoint(-87.6220, 41.8835), 4326)),
(v_tenant_id, 'The Pour House Coffee',   'coffee',    NULL,                ST_SetSRID(ST_MakePoint(-87.6252, 41.8810), 4326)),

-- Bakery (complementary)
(v_tenant_id, 'Paris Pastry Studio',     'bakery',    NULL,                ST_SetSRID(ST_MakePoint(-87.6260, 41.8830), 4326)),
(v_tenant_id, 'Rise & Shine Bakery',     'bakery',    'Rise & Shine',      ST_SetSRID(ST_MakePoint(-87.6215, 41.8840), 4326)),

-- Fast food (foot-traffic anchor)
(v_tenant_id, 'Burger Barn',             'fast_food', NULL,                ST_SetSRID(ST_MakePoint(-87.6240, 41.8818), 4326)),
(v_tenant_id, 'Quick Bites Express',     'fast_food', 'Quick Bites',       ST_SetSRID(ST_MakePoint(-87.6228, 41.8842), 4326)),
(v_tenant_id, 'Taco Town',              'fast_food', 'Taco Town',         ST_SetSRID(ST_MakePoint(-87.6255, 41.8805), 4326)),

-- Grocery
(v_tenant_id, 'Green Market Grocery',   'grocery',   NULL,                ST_SetSRID(ST_MakePoint(-87.6238, 41.8845), 4326)),
(v_tenant_id, 'City Provisions',        'grocery',   'City Provisions',   ST_SetSRID(ST_MakePoint(-87.6222, 41.8810), 4326)),

-- Convenience
(v_tenant_id, 'QuickStop Mart',         'convenience', NULL,              ST_SetSRID(ST_MakePoint(-87.6248, 41.8823), 4326)),
(v_tenant_id, 'Loop Convenience Plus',  'convenience', NULL,              ST_SetSRID(ST_MakePoint(-87.6219, 41.8833), 4326));

-- ── Points of Interest — River North area ─────────────────────────────────────
INSERT INTO pois (tenant_id, name, category, brand, geom) VALUES

-- Coffee
(v_tenant_id, 'The Daily Grind',         'coffee',    'Daily Grind',       ST_SetSRID(ST_MakePoint(-87.6340, 41.8925), 4326)),
(v_tenant_id, 'Lakefront Roasters',      'coffee',    NULL,                ST_SetSRID(ST_MakePoint(-87.6300, 41.8910), 4326)),

-- Bakery
(v_tenant_id, 'Sweet Provisions Bakery', 'bakery',    'Sweet Provisions',  ST_SetSRID(ST_MakePoint(-87.6330, 41.8930), 4326)),
(v_tenant_id, 'Artisan Crust',           'bakery',    NULL,                ST_SetSRID(ST_MakePoint(-87.6325, 41.8905), 4326)),

-- Fast food
(v_tenant_id, 'Sub Station Express',     'fast_food', 'Sub Station',       ST_SetSRID(ST_MakePoint(-87.6345, 41.8920), 4326)),
(v_tenant_id, 'Pizza Pronto',            'fast_food', NULL,                ST_SetSRID(ST_MakePoint(-87.6305, 41.8912), 4326)),
(v_tenant_id, 'Wrap & Roll',             'fast_food', 'Wrap & Roll',       ST_SetSRID(ST_MakePoint(-87.6315, 41.8935), 4326)),

-- Grocery
(v_tenant_id, 'Whole Harvest Market',    'grocery',   'Whole Harvest',     ST_SetSRID(ST_MakePoint(-87.6320, 41.8940), 4326)),
(v_tenant_id, 'Fresh Field Grocery',     'grocery',   NULL,                ST_SetSRID(ST_MakePoint(-87.6310, 41.8900), 4326)),

-- Convenience
(v_tenant_id, 'River North Minimart',    'convenience', NULL,              ST_SetSRID(ST_MakePoint(-87.6335, 41.8915), 4326)),

-- Retail (complementary)
(v_tenant_id, 'Michigan Ave Apparel',    'retail',    NULL,                ST_SetSRID(ST_MakePoint(-87.6298, 41.8922), 4326)),
(v_tenant_id, 'North Side Gifts',        'retail',    NULL,                ST_SetSRID(ST_MakePoint(-87.6350, 41.8908), 4326));

-- ── Points of Interest — Lincoln Park area ────────────────────────────────────
INSERT INTO pois (tenant_id, name, category, brand, geom) VALUES

-- Coffee
(v_tenant_id, 'Uptown Roasters',         'coffee',    NULL,                ST_SetSRID(ST_MakePoint(-87.6500, 41.9250), 4326)),
(v_tenant_id, 'Brew & Bean Lincoln',     'coffee',    'Brew & Bean',       ST_SetSRID(ST_MakePoint(-87.6468, 41.9235), 4326)),

-- Bakery
(v_tenant_id, 'Lincoln Park Bakehouse',  'bakery',    NULL,                ST_SetSRID(ST_MakePoint(-87.6490, 41.9255), 4326)),
(v_tenant_id, 'Morning Bloom Bakery',    'bakery',    'Morning Bloom',     ST_SetSRID(ST_MakePoint(-87.6475, 41.9245), 4326)),

-- Fast food
(v_tenant_id, 'Burger Buddy LP',         'fast_food', 'Burger Buddy',      ST_SetSRID(ST_MakePoint(-87.6480, 41.9260), 4326)),
(v_tenant_id, 'Sandwich Shoppe',         'fast_food', NULL,                ST_SetSRID(ST_MakePoint(-87.6500, 41.9230), 4326)),
(v_tenant_id, 'Noodle Box',              'fast_food', 'Noodle Box',        ST_SetSRID(ST_MakePoint(-87.6465, 41.9248), 4326)),

-- Grocery
(v_tenant_id, 'Neighbourhood Market',    'grocery',   NULL,                ST_SetSRID(ST_MakePoint(-87.6490, 41.9265), 4326)),
(v_tenant_id, 'Park Side Provisions',    'grocery',   'Park Side',         ST_SetSRID(ST_MakePoint(-87.6478, 41.9238), 4326)),

-- Convenience
(v_tenant_id, 'Lincoln Minimart',        'convenience', NULL,              ST_SetSRID(ST_MakePoint(-87.6495, 41.9252), 4326));

-- ── Points of Interest — Wicker Park area ─────────────────────────────────────
INSERT INTO pois (tenant_id, name, category, brand, geom) VALUES

-- Coffee
(v_tenant_id, 'Dark Matter East',        'coffee',    'Dark Matter Coffee', ST_SetSRID(ST_MakePoint(-87.6800, 41.9095), 4326)),
(v_tenant_id, 'Ground Floor Wicker',     'coffee',    NULL,                ST_SetSRID(ST_MakePoint(-87.6760, 41.9080), 4326)),

-- Bakery
(v_tenant_id, 'Wicker Bakes',            'bakery',    NULL,                ST_SetSRID(ST_MakePoint(-87.6795, 41.9085), 4326)),
(v_tenant_id, 'Flour & Butter',          'bakery',    NULL,                ST_SetSRID(ST_MakePoint(-87.6770, 41.9092), 4326)),

-- Fast food
(v_tenant_id, 'Burger Block',            'fast_food', NULL,                ST_SetSRID(ST_MakePoint(-87.6785, 41.9100), 4326)),
(v_tenant_id, 'Street Taco Hub',         'fast_food', 'Street Taco',       ST_SetSRID(ST_MakePoint(-87.6775, 41.9075), 4326)),
(v_tenant_id, 'Wing Stop Wicker',        'fast_food', 'Wing Stop',         ST_SetSRID(ST_MakePoint(-87.6800, 41.9090), 4326)),

-- Grocery
(v_tenant_id, 'People''s Grocery',       'grocery',   NULL,                ST_SetSRID(ST_MakePoint(-87.6780, 41.9105), 4326)),
(v_tenant_id, 'West Town Market',        'grocery',   'West Town',         ST_SetSRID(ST_MakePoint(-87.6790, 41.9078), 4326)),

-- Convenience
(v_tenant_id, 'Wicker Park Minimart',    'convenience', NULL,              ST_SetSRID(ST_MakePoint(-87.6795, 41.9088), 4326)),

-- Retail
(v_tenant_id, 'Milwaukee Ave Vintage',   'retail',    NULL,                ST_SetSRID(ST_MakePoint(-87.6772, 41.9096), 4326));

-- ── Points of Interest — Hyde Park area ───────────────────────────────────────
INSERT INTO pois (tenant_id, name, category, brand, geom) VALUES

-- Coffee
(v_tenant_id, 'Hyde Park Roasters',      'coffee',    NULL,                ST_SetSRID(ST_MakePoint(-87.5920, 41.7950), 4326)),
(v_tenant_id, 'South Side Brew',         'coffee',    NULL,                ST_SetSRID(ST_MakePoint(-87.5895, 41.7938), 4326)),

-- Bakery
(v_tenant_id, 'Morning Flour Bakery',    'bakery',    'Morning Flour',     ST_SetSRID(ST_MakePoint(-87.5915, 41.7945), 4326)),

-- Fast food
(v_tenant_id, 'Subs & Salads South',     'fast_food', NULL,                ST_SetSRID(ST_MakePoint(-87.5900, 41.7958), 4326)),
(v_tenant_id, 'Burger Basket South',     'fast_food', 'Burger Basket',     ST_SetSRID(ST_MakePoint(-87.5912, 41.7935), 4326)),
(v_tenant_id, 'Pizza by the Slice',      'fast_food', NULL,                ST_SetSRID(ST_MakePoint(-87.5890, 41.7948), 4326)),

-- Grocery
(v_tenant_id, 'Hyde Park Co-op',         'grocery',   'Hyde Park Co-op',   ST_SetSRID(ST_MakePoint(-87.5905, 41.7960), 4326)),
(v_tenant_id, 'South Side Fresh Market', 'grocery',   NULL,                ST_SetSRID(ST_MakePoint(-87.5920, 41.7940), 4326)),

-- Convenience
(v_tenant_id, 'Hyde Park Express Mart',  'convenience', NULL,              ST_SetSRID(ST_MakePoint(-87.5898, 41.7952), 4326)),
(v_tenant_id, 'Midway Convenience',      'convenience', NULL,              ST_SetSRID(ST_MakePoint(-87.5900, 41.7935), 4326)),

-- Office (complementary for coffee)
(v_tenant_id, 'University Admin Bldg',   'office',    NULL,                ST_SetSRID(ST_MakePoint(-87.5910, 41.7948), 4326)),
(v_tenant_id, 'Midway Research Center',  'office',    NULL,                ST_SetSRID(ST_MakePoint(-87.5885, 41.7955), 4326));

-- ── Seed scores for portfolio ranking ─────────────────────────────────────────
-- Pre-seeded scores allow /v1/portfolio/rank to return results without
-- requiring analyze to have been called first.
INSERT INTO scores (site_id, score_total, drivers_json, competitor_summary, market_summary, radius_m, industry_template)
VALUES
(
    '11111111-0000-0000-0000-000000000001',
    72.5,
    '[{"name":"Competitor Pressure","impact":8.0,"reason":"Moderate competition in Loop."},{"name":"Category Mix","impact":15.0,"reason":"Rich retail environment."},{"name":"Market Density","impact":25.0,"reason":"Dense urban corridor."},{"name":"Foot Traffic Potential","impact":20.0,"reason":"High anchor density."},{"name":"Brand Gap","impact":4.5,"reason":"Category present but room to win."}]',
    '{"coffee":3,"bakery":2,"fast_food":3,"grocery":2,"convenience":2}',
    '{"total_pois_in_radius":12,"poi_density_per_km2":23.5,"area_km2":8.04,"foot_traffic_indicators":7,"market_activity_score":89}',
    1600,
    'coffee'
),
(
    '11111111-0000-0000-0000-000000000002',
    81.0,
    '[{"name":"Competitor Pressure","impact":14.0,"reason":"Only 2 competitors."},{"name":"Category Mix","impact":20.0,"reason":"Excellent co-tenancy."},{"name":"Market Density","impact":25.0,"reason":"Prime tourist corridor."},{"name":"Foot Traffic Potential","impact":20.0,"reason":"Multiple anchors."},{"name":"Brand Gap","impact":2.0,"reason":"Competitive but winnable."}]',
    '{"coffee":2,"bakery":2,"fast_food":3,"grocery":2,"convenience":1,"retail":2}',
    '{"total_pois_in_radius":12,"poi_density_per_km2":25.1,"area_km2":8.04,"foot_traffic_indicators":8,"market_activity_score":95}',
    1600,
    'coffee'
),
(
    '11111111-0000-0000-0000-000000000003',
    65.0,
    '[{"name":"Competitor Pressure","impact":14.0,"reason":"2 competitors, manageable."},{"name":"Category Mix","impact":15.0,"reason":"Bakeries and grocery present."},{"name":"Market Density","impact":18.0,"reason":"Solid neighbourhood density."},{"name":"Foot Traffic Potential","impact":13.0,"reason":"Good anchor mix."},{"name":"Brand Gap","impact":5.0,"reason":"Underserved vs. area size."}]',
    '{"coffee":2,"bakery":2,"fast_food":3,"grocery":2,"convenience":1}',
    '{"total_pois_in_radius":10,"poi_density_per_km2":12.4,"area_km2":8.04,"foot_traffic_indicators":6,"market_activity_score":76}',
    1600,
    'coffee'
),
(
    '11111111-0000-0000-0000-000000000004',
    58.5,
    '[{"name":"Competitor Pressure","impact":8.0,"reason":"Moderate coffee density."},{"name":"Category Mix","impact":15.0,"reason":"Artisan retail mix strong."},{"name":"Market Density","impact":12.0,"reason":"Moderate emerging area."},{"name":"Foot Traffic Potential","impact":13.0,"reason":"Several anchors present."},{"name":"Brand Gap","impact":10.5,"reason":"Brand gap exists."}]',
    '{"coffee":2,"bakery":2,"fast_food":3,"grocery":2,"convenience":1,"retail":1}',
    '{"total_pois_in_radius":11,"poi_density_per_km2":10.2,"area_km2":8.04,"foot_traffic_indicators":6,"market_activity_score":68}',
    1600,
    'coffee'
),
(
    '11111111-0000-0000-0000-000000000005',
    47.0,
    '[{"name":"Competitor Pressure","impact":14.0,"reason":"Only 2 coffee competitors."},{"name":"Category Mix","impact":10.0,"reason":"Limited complementary mix."},{"name":"Market Density","impact":12.0,"reason":"Lower commercial density."},{"name":"Foot Traffic Potential","impact":7.0,"reason":"University foot traffic."},{"name":"Brand Gap","impact":4.0,"reason":"Underserved vs. north side."}]',
    '{"coffee":2,"bakery":1,"fast_food":3,"grocery":2,"convenience":2,"office":2}',
    '{"total_pois_in_radius":12,"poi_density_per_km2":8.7,"area_km2":8.04,"foot_traffic_indicators":8,"market_activity_score":61}',
    1600,
    'coffee'
)
ON CONFLICT (id) DO NOTHING;

-- ── Demo API Key ───────────────────────────────────────────────────────────────
-- Dev key: rk_rastera_demo_dev_0000000000000000000000
-- SHA-256:  9a12689a0aa08e848f3bec7b51ea9533016388b3b69fd4c45544fd73c6b12bdd
-- This key is for local development only.  Generate a real key in production
-- with: python scripts/create_api_key.py --tenant-slug demo-coffee --name prod
INSERT INTO tenant_api_keys (tenant_id, name, key_hash)
SELECT
    v_tenant_id,
    'dev',
    '9a12689a0aa08e848f3bec7b51ea9533016388b3b69fd4c45544fd73c6b12bdd'
WHERE NOT EXISTS (
    SELECT 1 FROM tenant_api_keys WHERE tenant_id = v_tenant_id AND name = 'dev'
);

END $$;
