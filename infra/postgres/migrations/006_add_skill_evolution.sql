-- migrate:up

-- Skill quality metrics — tracks how well each skill performs per agent
CREATE TABLE IF NOT EXISTS ${SCHEMA}.skill_metrics (
    id BIGSERIAL PRIMARY KEY,
    skill_id INT NOT NULL REFERENCES ${SCHEMA}.skills(id) ON DELETE CASCADE,
    agent_name VARCHAR(64) NOT NULL,
    times_selected INT DEFAULT 0,       -- times skill was in system prompt for a task
    times_applied INT DEFAULT 0,        -- times agent actually used the skill
    times_completed INT DEFAULT 0,      -- tasks completed successfully with skill
    times_fallback INT DEFAULT 0,       -- times skill was selected but not helpful
    last_applied_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (skill_id, agent_name)
);

CREATE INDEX IF NOT EXISTS idx_skill_metrics_agent
    ON ${SCHEMA}.skill_metrics(agent_name);
CREATE INDEX IF NOT EXISTS idx_skill_metrics_skill
    ON ${SCHEMA}.skill_metrics(skill_id);

-- Skill versions — immutable version history with lineage tracking
CREATE TABLE IF NOT EXISTS ${SCHEMA}.skill_versions (
    id BIGSERIAL PRIMARY KEY,
    skill_id INT NOT NULL REFERENCES ${SCHEMA}.skills(id) ON DELETE CASCADE,
    version INT NOT NULL DEFAULT 1,
    origin VARCHAR(16) NOT NULL DEFAULT 'imported',
        -- imported: from file import
        -- fixed: in-place repair of broken skill
        -- derived: enhanced version from parent(s)
        -- captured: novel pattern extracted from execution
    parent_version_ids BIGINT[],         -- references to parent skill_versions.id
    generation INT NOT NULL DEFAULT 0,   -- distance from original (0 = imported)
    change_summary TEXT,                 -- LLM-generated description of what changed
    content_snapshot TEXT NOT NULL,       -- full skill content at this version
    is_active BOOLEAN DEFAULT TRUE,      -- only one active version per skill
    created_by VARCHAR(64),              -- agent name or 'system'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (skill_id, version)
);

CREATE INDEX IF NOT EXISTS idx_skill_versions_skill_active
    ON ${SCHEMA}.skill_versions(skill_id, is_active);

-- Evolution proposals — agents suggest skill changes, humans approve
CREATE TABLE IF NOT EXISTS ${SCHEMA}.skill_evolution_proposals (
    id BIGSERIAL PRIMARY KEY,
    skill_id INT REFERENCES ${SCHEMA}.skills(id) ON DELETE SET NULL,
        -- NULL for CAPTURED (new skill, no existing skill_id yet)
    evolution_type VARCHAR(16) NOT NULL,
        -- fix, derived, captured
    proposed_by VARCHAR(64) NOT NULL,    -- agent name
    status VARCHAR(16) NOT NULL DEFAULT 'pending',
        -- pending, approved, rejected, applied
    direction TEXT NOT NULL,             -- what to change and why
    proposed_content TEXT,               -- full proposed skill content
    proposed_name VARCHAR(128),          -- for captured: new skill name
    proposed_description TEXT,           -- for captured: new skill description
    proposed_tags TEXT[],                -- for captured: new skill tags
    source_task_key VARCHAR(16),         -- task that triggered this proposal
    source_conversation_id VARCHAR(128), -- conversation that triggered this
    review_notes TEXT,                   -- human reviewer notes
    reviewed_by VARCHAR(64),             -- human reviewer
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evolution_proposals_status
    ON ${SCHEMA}.skill_evolution_proposals(status);
CREATE INDEX IF NOT EXISTS idx_evolution_proposals_skill
    ON ${SCHEMA}.skill_evolution_proposals(skill_id);

-- Seed initial versions for all existing skills
INSERT INTO ${SCHEMA}.skill_versions (skill_id, version, origin, generation, content_snapshot, is_active, created_by)
SELECT id, 1, 'imported', 0, content, true, 'system'
FROM ${SCHEMA}.skills
WHERE NOT EXISTS (
    SELECT 1 FROM ${SCHEMA}.skill_versions sv WHERE sv.skill_id = skills.id
);

-- migrate:down
DROP TABLE IF EXISTS ${SCHEMA}.skill_evolution_proposals;
DROP TABLE IF EXISTS ${SCHEMA}.skill_versions;
DROP TABLE IF EXISTS ${SCHEMA}.skill_metrics;
