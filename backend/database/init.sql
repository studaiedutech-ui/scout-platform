-- Initial database setup for S.C.O.U.T. Platform
-- This script will be run by Docker on first startup

-- Create database if it doesn't exist
-- CREATE DATABASE scout_db;

-- Extensions for PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Indexes for better performance
-- These will be created by SQLAlchemy, but can be added here for reference

-- Create indexes on frequently queried columns
-- CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
-- CREATE INDEX IF NOT EXISTS idx_users_company_id ON users(company_id);
-- CREATE INDEX IF NOT EXISTS idx_companies_slug ON companies(slug);
-- CREATE INDEX IF NOT EXISTS idx_jobs_company_id ON jobs(company_id);
-- CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
-- CREATE INDEX IF NOT EXISTS idx_candidates_job_id ON candidates(job_id);
-- CREATE INDEX IF NOT EXISTS idx_candidates_status ON candidates(status);
-- CREATE INDEX IF NOT EXISTS idx_assessments_candidate_id ON assessments(candidate_id);
-- CREATE INDEX IF NOT EXISTS idx_assessments_session_id ON assessments(session_id);

-- Sample data for development (optional)
-- This can be uncommented for local development

/*
-- Sample company
INSERT INTO companies (name, slug, website_url, industry, size, subscription_plan, onboarding_completed) 
VALUES ('TechCorp', 'techcorp', 'https://techcorp.com', 'Technology', 'medium', 'pro', true)
ON CONFLICT DO NOTHING;

-- Sample user
INSERT INTO users (email, hashed_password, full_name, role, company_id, is_email_verified)
VALUES ('admin@techcorp.com', '$2b$12$sample_hashed_password', 'Admin User', 'admin', 1, true)
ON CONFLICT DO NOTHING;

-- Sample job
INSERT INTO jobs (title, description, slug, company_id, created_by, status, assessment_link)
VALUES (
    'Senior Software Engineer', 
    'We are looking for a senior software engineer to join our team...', 
    'senior-software-engineer', 
    1, 
    1, 
    'active',
    'https://app.scout-platform.com/apply/techcorp/senior-software-engineer'
)
ON CONFLICT DO NOTHING;
*/