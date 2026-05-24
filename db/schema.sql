-- ============================================================
-- Commercial Intelligence Schema for ML_APP
-- PostgreSQL 13+
-- ============================================================

-- ── Berth Economics ─────────────────────────────────────────
DROP TABLE IF EXISTS commercial_assignments CASCADE;
DROP TABLE IF EXISTS pricing_rules CASCADE;
DROP TABLE IF EXISTS contract_obligations CASCADE;
DROP TABLE IF EXISTS vessel_companies CASCADE;
DROP TABLE IF EXISTS berth_economics CASCADE;

CREATE TABLE berth_economics (
    berth_code              VARCHAR(20) PRIMARY KEY,
    berth_name              VARCHAR(100),
    berth_class             VARCHAR(20)  NOT NULL DEFAULT 'STANDARD',   -- PREMIUM / STANDARD / BUDGET
    specialization          VARCHAR(50)  NOT NULL DEFAULT 'General',    -- Container / Oil_Tanker / RoRo / Multipurpose / Chemical
    base_operating_cost_ph  NUMERIC(12,2) NOT NULL DEFAULT 900.0,
    -- Container rates
    rate_20ft_container     NUMERIC(12,2) DEFAULT 600.0,
    rate_40ft_container     NUMERIC(12,2) DEFAULT 800.0,
    rate_reefer_container   NUMERIC(12,2) DEFAULT 1200.0,
    -- Bulk / general rates (per ton)
    rate_ton_bulk           NUMERIC(12,2) DEFAULT 22.0,
    rate_ton_general        NUMERIC(12,2) DEFAULT 28.0,
    -- Oil tanker rates (per call, size bracket)
    rate_oil_small          NUMERIC(12,2) DEFAULT 2500.0,
    rate_oil_medium         NUMERIC(12,2) DEFAULT 4500.0,
    rate_oil_large          NUMERIC(12,2) DEFAULT 7000.0,
    -- RoRo rate (per vehicle)
    rate_vehicle            NUMERIC(12,2) DEFAULT 75.0,
    -- Chemical (per call)
    rate_chemical_call      NUMERIC(12,2) DEFAULT 3500.0,
    -- Economics
    monthly_fixed_cost      NUMERIC(14,2) DEFAULT 30000.0,
    avg_revenue_per_call    NUMERIC(14,2) DEFAULT 60000.0,
    profit_margin_est       NUMERIC(6,4)  DEFAULT 0.45,
    utilization_target_low  NUMERIC(4,3)  DEFAULT 0.70,
    utilization_target_high NUMERIC(4,3)  DEFAULT 0.85,
    -- Dynamic pricing thresholds
    dp_high_threshold       NUMERIC(4,3)  DEFAULT 0.90,
    dp_low_threshold        NUMERIC(4,3)  DEFAULT 0.50,
    dp_high_premium         NUMERIC(4,3)  DEFAULT 0.15,
    dp_low_discount         NUMERIC(4,3)  DEFAULT 0.10,
    -- Meta
    created_at              TIMESTAMPTZ   DEFAULT NOW(),
    updated_at              TIMESTAMPTZ   DEFAULT NOW()
);

-- ── Vessel Companies ────────────────────────────────────────
CREATE TABLE vessel_companies (
    company_id              VARCHAR(50) PRIMARY KEY,
    display_name            VARCHAR(150) NOT NULL,
    tier                    VARCHAR(30)  NOT NULL DEFAULT 'STANDARD',   -- VIP / PREMIUM / STANDARD / STRATEGIC_PROSPECT
    annual_contract_value   NUMERIC(16,2) DEFAULT 0,
    visits_per_year         INTEGER       DEFAULT 0,
    contract_start          DATE,
    contract_expiry         DATE,
    is_contract             BOOLEAN       DEFAULT FALSE,
    discount_percentage     NUMERIC(5,2)  DEFAULT 0.0,
    discount_reason         VARCHAR(200)  DEFAULT '',
    additional_benefits     TEXT[]        DEFAULT '{}',
    contact_person          VARCHAR(100)  DEFAULT '',
    contact_title           VARCHAR(100)  DEFAULT '',
    email                   VARCHAR(150)  DEFAULT '',
    phone                   VARCHAR(50)   DEFAULT '',
    notes                   TEXT          DEFAULT '',
    created_at              TIMESTAMPTZ   DEFAULT NOW(),
    updated_at              TIMESTAMPTZ   DEFAULT NOW()
);

-- ── Contract Obligations ────────────────────────────────────
CREATE TABLE contract_obligations (
    id                      SERIAL PRIMARY KEY,
    company_id              VARCHAR(50) NOT NULL REFERENCES vessel_companies(company_id) ON DELETE CASCADE,
    guaranteed_berth_types  TEXT[]      DEFAULT '{}',
    guaranteed_slots_month  INTEGER     DEFAULT 0,
    priority_level          INTEGER     DEFAULT 4,
    sla_turnaround_hours    NUMERIC(6,2) DEFAULT 48.0,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ── Pricing Rules ────────────────────────────────────────────
CREATE TABLE pricing_rules (
    id                      SERIAL PRIMARY KEY,
    rule_name               VARCHAR(100) NOT NULL,
    berth_type              VARCHAR(50)  DEFAULT 'ALL',          -- Container / Oil_Tanker / ALL
    utilization_high        NUMERIC(4,3) DEFAULT 0.90,
    utilization_low         NUMERIC(4,3) DEFAULT 0.50,
    premium_pct             NUMERIC(5,2) DEFAULT 15.0,
    discount_pct            NUMERIC(5,2) DEFAULT 10.0,
    off_peak_discount_pct   NUMERIC(5,2) DEFAULT 20.0,
    weekend_discount_pct    NUMERIC(5,2) DEFAULT 30.0,
    q4_premium_pct          NUMERIC(5,2) DEFAULT 10.0,
    q1_discount_pct         NUMERIC(5,2) DEFAULT 10.0,
    hazmat_premium_pct      NUMERIC(5,2) DEFAULT 25.0,
    is_active               BOOLEAN      DEFAULT TRUE,
    created_at              TIMESTAMPTZ  DEFAULT NOW()
);

-- ── Commercial Assignments (Learning Data) ───────────────────
CREATE TABLE commercial_assignments (
    id                      SERIAL PRIMARY KEY,
    vessel_id               VARCHAR(50),
    vessel_name             VARCHAR(100),
    berth_code              VARCHAR(20),
    vessel_company          VARCHAR(50),
    vessel_type             VARCHAR(50),
    partnership_tier        VARCHAR(30),
    predicted_revenue       NUMERIC(14,2) DEFAULT 0,
    actual_revenue          NUMERIC(14,2) DEFAULT 0,
    predicted_profit        NUMERIC(14,2) DEFAULT 0,
    actual_profit           NUMERIC(14,2) DEFAULT 0,
    planned_turnaround_hrs  NUMERIC(6,2)  DEFAULT 0,
    actual_turnaround_hrs   NUMERIC(6,2)  DEFAULT 0,
    sla_target_hrs          NUMERIC(6,2)  DEFAULT 48,
    sla_met                 BOOLEAN       DEFAULT TRUE,
    discount_applied_pct    NUMERIC(5,2)  DEFAULT 0,
    dynamic_multiplier      NUMERIC(6,4)  DEFAULT 1.0,
    decision_mode           VARCHAR(30)   DEFAULT 'balanced',
    assignment_dt           TIMESTAMPTZ   DEFAULT NOW()
);

-- ── Indexes ──────────────────────────────────────────────────
CREATE INDEX idx_ca_vessel      ON commercial_assignments(vessel_company);
CREATE INDEX idx_ca_berth       ON commercial_assignments(berth_code);
CREATE INDEX idx_ca_tier        ON commercial_assignments(partnership_tier);
CREATE INDEX idx_ca_dt          ON commercial_assignments(assignment_dt DESC);
CREATE INDEX idx_vc_tier        ON vessel_companies(tier);
