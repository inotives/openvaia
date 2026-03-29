-- migrate:up

-- Skill definitions
CREATE TABLE IF NOT EXISTS platform.skills (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(128) UNIQUE NOT NULL,
    description TEXT,
    content     TEXT,
    tags        TEXT[] NOT NULL DEFAULT '{}',
    global      BOOLEAN NOT NULL DEFAULT false,
    enabled     BOOLEAN NOT NULL DEFAULT true,
    status      VARCHAR(16) NOT NULL DEFAULT 'active'
                CHECK (status IN ('draft', 'active', 'rejected', 'inactive')),
    created_by  VARCHAR(64),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_skills_tags
    ON platform.skills USING GIN (tags);

CREATE INDEX IF NOT EXISTS idx_skills_status
    ON platform.skills (status);

CREATE INDEX IF NOT EXISTS idx_skills_global_enabled
    ON platform.skills (global, enabled);

-- Agent-skill assignments
CREATE TABLE IF NOT EXISTS platform.agent_skills (
    id          SERIAL PRIMARY KEY,
    agent_name  VARCHAR(64) NOT NULL,
    skill_id    INT NOT NULL REFERENCES platform.skills(id) ON DELETE CASCADE,
    priority    INT NOT NULL DEFAULT 100,
    UNIQUE (agent_name, skill_id)
);

CREATE INDEX IF NOT EXISTS idx_agent_skills_agent
    ON platform.agent_skills (agent_name);

-- Agent runtime configs (overridable via UI/DB)
CREATE TABLE IF NOT EXISTS platform.agent_configs (
    id          SERIAL PRIMARY KEY,
    agent_name  VARCHAR(64) NOT NULL,
    key         VARCHAR(128) NOT NULL,
    value       TEXT,
    source      VARCHAR(16) NOT NULL DEFAULT 'yaml',
    description TEXT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (agent_name, key)
);

CREATE INDEX IF NOT EXISTS idx_agent_configs_agent
    ON platform.agent_configs (agent_name);

-- migrate:down

DROP TABLE IF EXISTS platform.agent_configs;
DROP TABLE IF EXISTS platform.agent_skills;
DROP TABLE IF EXISTS platform.skills;
