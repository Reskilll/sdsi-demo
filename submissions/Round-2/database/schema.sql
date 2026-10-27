-- EBC: External Business Center - PostgreSQL Schema
-- Run: psql -U postgres -d ebc -f schema.sql

CREATE DATABASE ebc;

\c ebc;

-- Groups (GDC divisions)
CREATE TABLE groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    target_lakh DECIMAL(12,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Departments
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    group_id INTEGER REFERENCES groups(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Leaders (group persons)
CREATE TABLE leaders (
    id VARCHAR(5) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    skill_factor DECIMAL(3,2) DEFAULT 1.0,
    active_deals INTEGER DEFAULT 0,
    group_id INTEGER REFERENCES groups(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Regions
CREATE TABLE regions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    timezone_desc VARCHAR(100),
    cost_modifier DECIMAL(3,2) DEFAULT 1.0
);

-- Clients
CREATE TABLE clients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    region_id INTEGER REFERENCES regions(id),
    procurement_dept VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Business Models
CREATE TABLE business_models (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description TEXT
);

-- Skill Divisions
CREATE TABLE divisions (
    id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    staff_count INTEGER DEFAULT 0
);

-- Resources
CREATE TABLE resources (
    id VARCHAR(5) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    skill_div_id VARCHAR(10) REFERENCES divisions(id),
    category VARCHAR(50),
    group_id INTEGER REFERENCES groups(id),
    department_id INTEGER REFERENCES departments(id),
    tenure_years INTEGER DEFAULT 1,
    rating DECIMAL(3,1) DEFAULT 3.5,
    status VARCHAR(20) DEFAULT 'Bench',
    engaged_in_opp VARCHAR(10)
);

-- Opportunities
CREATE TABLE opportunities (
    id VARCHAR(10) PRIMARY KEY,
    leader_id VARCHAR(5) REFERENCES leaders(id),
    client_id INTEGER REFERENCES clients(id),
    source VARCHAR(50),
    business_model VARCHAR(50),
    pricing VARCHAR(50),
    procurement_dept VARCHAR(100),
    value_lakh DECIMAL(10,2),
    title VARCHAR(200),
    status VARCHAR(20) DEFAULT 'open',
    stage INTEGER DEFAULT 0,
    reached INTEGER DEFAULT 0,
    competitor VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    close_date TIMESTAMP,
    expected_close TIMESTAMP,
    due_date TIMESTAMP,
    cycle_days INTEGER DEFAULT 90,
    last_update TIMESTAMP DEFAULT NOW(),
    lesson TEXT,
    win_probability DECIMAL(5,4)
);

-- Opportunity Status History
CREATE TABLE opportunity_history (
    id SERIAL PRIMARY KEY,
    opportunity_id VARCHAR(10) REFERENCES opportunities(id),
    stage_name VARCHAR(100),
    entry_date TIMESTAMP DEFAULT NOW()
);

-- Opportunity Reasons
CREATE TABLE opportunity_reasons (
    id SERIAL PRIMARY KEY,
    opportunity_id VARCHAR(10) REFERENCES opportunities(id),
    reason VARCHAR(150)
);

-- Services
CREATE TABLE services (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200),
    business_model_id INTEGER REFERENCES business_models(id)
);

-- Skill Mix (what each service needs)
CREATE TABLE skill_mix (
    id SERIAL PRIMARY KEY,
    service_id INTEGER REFERENCES services(id),
    division_id VARCHAR(10) REFERENCES divisions(id),
    share DECIMAL(5,4)
);

-- Audit Trail
CREATE TABLE audit_trail (
    id SERIAL PRIMARY KEY,
    event_time TIMESTAMP DEFAULT NOW(),
    actor VARCHAR(150),
    role VARCHAR(100),
    action VARCHAR(200),
    detail TEXT,
    ai_assisted BOOLEAN DEFAULT FALSE,
    approved_by VARCHAR(150)
);

-- Reminders
CREATE TABLE reminders (
    id SERIAL PRIMARY KEY,
    reminder_time TIMESTAMP,
    text TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Bench capacity holds
CREATE TABLE capacity_holds (
    id SERIAL PRIMARY KEY,
    start_week INTEGER,
    duration_weeks INTEGER,
    client_name VARCHAR(150),
    division_id VARCHAR(10) REFERENCES divisions(id),
    people_needed DECIMAL(5,2)
);

-- Weekly briefs
CREATE TABLE weekly_briefs (
    id SERIAL PRIMARY KEY,
    week_start DATE,
    period_days INTEGER DEFAULT 7,
    head_text TEXT,
    sections_json TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Recognition
CREATE TABLE recognitions (
    id SERIAL PRIMARY KEY,
    kind VARCHAR(50),
    target_name VARCHAR(150),
    reason TEXT,
    recorded_at TIMESTAMP DEFAULT NOW()
);

-- Sources
CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50),
    base_conversion DECIMAL(3,2) DEFAULT 0.0
);

-- Insert sample seed data
INSERT INTO groups (name, target_lakh) VALUES
    ('Solution Development Group', 1400),
    ('Integrated App Dev & Operation Group', 1120),
    ('Digital CRM Group', 880),
    ('Delivery Excellence Group', 600);

INSERT INTO departments (name, group_id) VALUES
    ('Global Solution Part', 1),
    ('Advanced Development Part', 1),
    ('Knox Part', 1),
    ('Architecture Part', 1);

INSERT INTO regions (name, timezone_desc, cost_modifier) VALUES
    ('North America', 'US Eastern or Pacific time', 1.0),
    ('Europe', 'GMT or CET', 0.95),
    ('Asia-Pacific', 'SGT or AEST', 1.05),
    ('Middle East', 'Gulf Standard Time', 0.9);

INSERT INTO leaders (id, name, skill_factor, active_deals, group_id) VALUES
    ('L1', 'Anita Rao', 1.15, 9, 1),
    ('L2', 'Rohit Verma', 0.85, 8, 2),
    ('L3', 'Meera Nair', 1.05, 7, 3),
    ('L4', 'Karan Shah', 0.70, 5, 4),
    ('L5', 'Priya Menon', 1.30, 9, 1),
    ('L6', 'Sanjay Iyer', 0.80, 7, 2),
    ('L7', 'Divya Kapoor', 0.95, 6, 3),
    ('L8', 'Arjun Reddy', 0.55, 3, 4),
    ('L9', 'Neha Gupta', 1.00, 7, 1),
    ('L10', 'Vikram Singh', 0.75, 4, 2);

INSERT INTO divisions (id, name, category, staff_count) VALUES
    ('java', 'Java', 'Technology', 31),
    ('py', 'Python', 'Technology', 18),
    ('js', 'JavaScript and React', 'Technology', 21),
    ('cloud', 'Cloud and DevOps', 'Technology', 18),
    ('sap', 'SAP', 'Platform', 13),
    ('sf', 'Salesforce', 'Platform', 16),
    ('knox', 'Knox', 'Platform', 10),
    ('snow', 'ServiceNow', 'Platform', 10),
    ('ba', 'Business analysis', 'General/Niche', 13),
    ('qa', 'QA and testing', 'General/Niche', 21),
    ('sec', 'Security', 'General/Niche', 10),
    ('lead', 'Tech lead', 'General/Niche', 13);

INSERT INTO business_models (name, description) VALUES
    ('Offshore', 'Monthly rate per resource'),
    ('Software Development', 'Fixed price or time and material'),
    ('Infra', 'Monthly retainer'),
    ('Security', 'Monthly retainer');

INSERT INTO sources (name, base_conversion) VALUES
    ('Leader network', 0.40),
    ('Client portal', 0.21),
    ('Referral', 0.50),
    ('Repeat client', 0.60),
    ('Cold outreach', 0.12),
    ('Partner', 0.36);

INSERT INTO clients (name, region_id, procurement_dept) VALUES
    ('Harborline Logistics', 1, 'Global Procurement'),
    ('Pinecrest Health Systems', 1, 'Vendor Management Office'),
    ('Cascade Energy', 1, 'Strategic Sourcing'),
    ('Lakeshore Insurance', 1, 'IT Procurement'),
    ('Brightwater Media', 1, 'Technology Sourcing'),
    ('Nordvik Bank', 2, 'Global Procurement'),
    ('Alpenland Retail', 2, 'Vendor Management Office'),
    ('Thames Utilities', 2, 'Strategic Sourcing'),
    ('Dune Petroleum Services', 4, 'Global Procurement'),
    ('Falcon Telecom', 4, 'Strategic Sourcing'),
    ('Meridian Retail Asia', 3, 'Technology Sourcing'),
    ('Tasman Energy', 3, 'IT Procurement');