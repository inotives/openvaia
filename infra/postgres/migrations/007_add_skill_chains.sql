-- migrate:up

-- Skill chains — ordered sequences of skills for task types
CREATE TABLE IF NOT EXISTS openvaia.skill_chains (
    id SERIAL PRIMARY KEY,
    name VARCHAR(64) NOT NULL UNIQUE,
    description TEXT,
    match_tags TEXT[] NOT NULL,              -- tags that trigger this chain
    match_keywords TEXT[],                   -- title keywords that trigger this chain
    steps JSONB NOT NULL,                    -- ordered array of steps
    -- steps format: [
    --   {"phase": "propose", "skills": ["spec_driven_proposal"], "gate": "human_approval"},
    --   {"phase": "implement", "skills": ["test_driven_development"]},
    -- ]
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add chain tracking to tasks
ALTER TABLE openvaia.tasks
    ADD COLUMN IF NOT EXISTS chain_id INT REFERENCES openvaia.skill_chains(id),
    ADD COLUMN IF NOT EXISTS chain_state JSONB;
-- chain_state format:
-- {
--   "current_phase": "implement",
--   "current_step_index": 4,
--   "completed_phases": ["propose", "specify", "design", "plan"],
--   "active_skills": ["test_driven_development"],
--   "started_at": "2026-04-01T10:00:00Z"
-- }

CREATE INDEX IF NOT EXISTS idx_skill_chains_active
    ON openvaia.skill_chains(is_active);
CREATE INDEX IF NOT EXISTS idx_tasks_chain
    ON openvaia.tasks(chain_id) WHERE chain_id IS NOT NULL;

-- migrate:down
ALTER TABLE openvaia.tasks DROP COLUMN IF EXISTS chain_state;
ALTER TABLE openvaia.tasks DROP COLUMN IF EXISTS chain_id;
DROP TABLE IF EXISTS openvaia.skill_chains;
