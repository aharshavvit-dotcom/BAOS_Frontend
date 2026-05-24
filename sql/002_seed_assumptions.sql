-- ============================================================
-- BAOS Seed Data — Default Assumptions for Chennai
-- ============================================================

-- Ensure Chennai port exists
INSERT INTO baos.port (port_id, port_code, port_name, country, timezone)
VALUES (
    'a0000000-0000-0000-0000-000000000001'::uuid,
    'INMAA',
    'Chennai Port',
    'India',
    'Asia/Kolkata'
) ON CONFLICT (port_code) DO NOTHING;

-- Seed default assumptions
INSERT INTO baos.assumption_config (assumption_id, port_id, assumption_key, assumption_value, unit, source_quality, confidence_multiplier, description)
VALUES
    (gen_random_uuid(), 'a0000000-0000-0000-0000-000000000001'::uuid, 'DEMURRAGE_RATE_USD_PER_HOUR', 500, 'USD/hour', 'ASSUMPTION', 0.80, 'Demurrage cost per hour of delay'),
    (gen_random_uuid(), 'a0000000-0000-0000-0000-000000000001'::uuid, 'FUEL_WAIT_RATE_USD_PER_HOUR', 150, 'USD/hour', 'ASSUMPTION', 0.80, 'Fuel burn cost while waiting at anchorage'),
    (gen_random_uuid(), 'a0000000-0000-0000-0000-000000000001'::uuid, 'SLA_PENALTY_USD_PER_HOUR', 1000, 'USD/hour', 'ASSUMPTION', 0.80, 'Penalty for SLA breach per hour'),
    (gen_random_uuid(), 'a0000000-0000-0000-0000-000000000001'::uuid, 'REVENUE_PER_TON_USD', 2.5, 'USD/ton', 'ASSUMPTION', 0.80, 'Average revenue per ton of cargo handled'),
    (gen_random_uuid(), 'a0000000-0000-0000-0000-000000000001'::uuid, 'UNASSIGNED_PENALTY_USD', 100000, 'USD', 'ASSUMPTION', 0.80, 'Penalty cost for unassigned vessel in optimizer'),
    (gen_random_uuid(), 'a0000000-0000-0000-0000-000000000001'::uuid, 'SCHEDULE_CHANGE_PENALTY_USD', 5000, 'USD', 'ASSUMPTION', 0.80, 'Cost of changing an existing schedule assignment'),
    (gen_random_uuid(), 'a0000000-0000-0000-0000-000000000001'::uuid, 'DEFAULT_PILOT_CAPACITY', 2, 'count', 'ASSUMPTION', 0.80, 'Number of pilots available at any time'),
    (gen_random_uuid(), 'a0000000-0000-0000-0000-000000000001'::uuid, 'DEFAULT_TUG_CAPACITY', 3, 'count', 'ASSUMPTION', 0.80, 'Number of tugs available at any time'),
    (gen_random_uuid(), 'a0000000-0000-0000-0000-000000000001'::uuid, 'DEFAULT_CHANNEL_CAPACITY', 1, 'count', 'ASSUMPTION', 0.80, 'Number of vessels that can transit channel simultaneously'),
    (gen_random_uuid(), 'a0000000-0000-0000-0000-000000000001'::uuid, 'DEFAULT_UKC_MARGIN_M', 0.5, 'meters', 'ASSUMPTION', 0.80, 'Under-keel clearance safety margin')
ON CONFLICT (port_id, assumption_key) DO NOTHING;
