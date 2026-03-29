-- migrate:up

CREATE SCHEMA IF NOT EXISTS platform;

-- Agents registry
CREATE TABLE IF NOT EXISTS platform.agents (
    name        VARCHAR(64) PRIMARY KEY,
    role        VARCHAR(128) NOT NULL DEFAULT '',
    status      VARCHAR(16) NOT NULL DEFAULT 'offline',
    last_seen   TIMESTAMPTZ DEFAULT NOW()
);

-- Communication spaces
CREATE TABLE IF NOT EXISTS platform.spaces (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(64) NOT NULL UNIQUE,
    type        VARCHAR(16) NOT NULL CHECK (type IN ('public', 'tasks', 'room', 'direct')),
    created_by  VARCHAR(64),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Space membership
CREATE TABLE IF NOT EXISTS platform.space_members (
    space_id    INT NOT NULL REFERENCES platform.spaces(id) ON DELETE CASCADE,
    agent_name  VARCHAR(64) NOT NULL,
    UNIQUE (space_id, agent_name)
);

-- Platform messages
CREATE TABLE IF NOT EXISTS platform.messages (
    id          BIGSERIAL PRIMARY KEY,
    from_agent  VARCHAR(64) NOT NULL,
    space_id    INT NOT NULL REFERENCES platform.spaces(id) ON DELETE CASCADE,
    body        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_space_created
    ON platform.messages (space_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_messages_from_agent
    ON platform.messages (from_agent);

-- Agent health status
CREATE TABLE IF NOT EXISTS platform.agent_status (
    id               BIGSERIAL PRIMARY KEY,
    agent_name       VARCHAR(64) NOT NULL,
    healthy          BOOLEAN DEFAULT true,
    details          JSONB DEFAULT '{}',
    checked_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_status_name_checked
    ON platform.agent_status (agent_name, checked_at DESC);

-- Platform key-value config
CREATE TABLE IF NOT EXISTS platform.config (
    key         VARCHAR(128) PRIMARY KEY,
    value       TEXT NOT NULL DEFAULT '',
    description TEXT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- migrate:down

DROP TABLE IF EXISTS platform.config;
DROP TABLE IF EXISTS platform.agent_status;
DROP TABLE IF EXISTS platform.messages;
DROP TABLE IF EXISTS platform.space_members;
DROP TABLE IF EXISTS platform.spaces;
DROP TABLE IF EXISTS platform.agents;
DROP SCHEMA IF EXISTS platform;
