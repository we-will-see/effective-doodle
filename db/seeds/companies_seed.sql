-- Seed data for coverage.companies
-- 8 companies for AgentOS v1 vertical slice
-- BSE codes verified: 2026-05-06

INSERT INTO coverage.companies (
    bse_code,
    nse_symbol,
    isin,
    legal_name,
    display_name,
    sector,
    sub_sector,
    market_cap_bucket,
    fy_convention,
    coverage_status,
    primary_analyst,
    notes
) VALUES
-- Core 3 (high conviction)
('543064', 'COHANCE', NULL, 'Cohance Lifesciences Limited', 'Cohance Lifesciences', 'Pharmaceuticals', 'API / CDMO', 'mid', 'apr-mar', 'active', 'Mohit', 'CDMO focused on Pharma; high conviction thesis'),
('544306', 'SAILIFE', NULL, 'Sai Life Sciences Limited', 'Sai Life Sciences', 'Pharmaceuticals', 'API / CDMO / CRDMO', 'mid', 'apr-mar', 'active', 'Mohit', 'Integrated CRDMO with discovery to manufacturing'),
('544449', 'ANTHEM', NULL, 'Anthem Biosciences Limited', 'Anthem Biosciences', 'Pharmaceuticals', 'CRDMO / Drug Discovery', 'mid', 'apr-mar', 'active', 'Mohit', 'Innovation-driven CRDMO; rare Indian discovery play'),

-- Additional 5 (placeholder for full cohort)
('540691', 'ASTERDM', NULL, 'Aster DM Healthcare Limited', 'Aster DM Healthcare', 'Healthcare', 'Hospitals', 'large', 'apr-mar', 'active', 'Mohit', 'Hospital chain; GCC + India presence'),
('542932', 'RKDL', NULL, 'Ravi Kumar Distilleries Limited', 'Ravi Kumar Distilleries', 'Consumer Staples', 'Alcohol Beverages', 'small', 'apr-mar', 'active', 'Mohit', 'Regional liquor player; niche positioning'),
('524667', 'PANACEABIO', NULL, 'Panacea Biotec Limited', 'Panacea Biotec', 'Pharmaceuticals', 'Vaccines / Biologics', 'mid', 'apr-mar', 'active', 'Mohit', 'Vaccine specialist; pediatric portfolio'),
('506808', 'WOCKPHARMA', NULL, 'Wockhardt Limited', 'Wockhardt', 'Pharmaceuticals', 'Branded Formulations / API', 'mid', 'apr-mar', 'active', 'Mohit', 'Legacy pharma; restructuring story'),
('500124', 'DRREDDY', NULL, 'Dr. Reddy''s Laboratories Limited', 'Dr. Reddys', 'Pharmaceuticals', 'Generics / Formulations / API', 'large', 'apr-mar', 'watchlist', 'Mohit', 'Large cap benchmark; acquisition history')

ON CONFLICT (bse_code) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    sector = EXCLUDED.sector,
    sub_sector = EXCLUDED.sub_sector,
    updated_at = now();
