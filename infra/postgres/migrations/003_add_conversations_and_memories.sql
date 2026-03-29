-- migrate:up

CREATE EXTENSION IF NOT EXISTS vector;

-- Conversation history
CREATE TABLE IF NOT EXISTS platform.conversations (
    id              BIGSERIAL PRIMARY KEY,
    conversation_id VARCHAR(128) NOT NULL,
    agent_name      VARCHAR(64) NOT NULL,
    role            VARCHAR(16) NOT NULL,
    content         TEXT,
    channel_type    VARCHAR(16) NOT NULL DEFAULT 'cli',
    tool_calls      JSONB,
    metadata        JSONB DEFAULT '{}',
    processed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_convid_created
    ON platform.conversations (conversation_id, created_at);

CREATE INDEX IF NOT EXISTS idx_conversations_agent_created
    ON platform.conversations (agent_name, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_conversations_channel_created
    ON platform.conversations (channel_type, created_at DESC);

-- Memory store (hybrid FTS + pgvector embedding search)
CREATE TABLE IF NOT EXISTS platform.memories (
    id          BIGSERIAL PRIMARY KEY,
    agent_name  VARCHAR(64) NOT NULL,
    content     TEXT NOT NULL,
    tags        TEXT[] NOT NULL DEFAULT '{}',
    tier        VARCHAR(8) NOT NULL DEFAULT 'short'
                CHECK (tier IN ('short', 'long')),
    embedding   vector(1024),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memories_agent_tier
    ON platform.memories (agent_name, tier);

CREATE INDEX IF NOT EXISTS idx_memories_tags
    ON platform.memories USING GIN (tags);

CREATE INDEX IF NOT EXISTS idx_memories_fts
    ON platform.memories USING GIN (to_tsvector('english', content));

CREATE INDEX IF NOT EXISTS idx_memories_embedding
    ON platform.memories USING hnsw (embedding vector_cosine_ops);

-- Research reports
CREATE TABLE IF NOT EXISTS platform.research_reports (
    id          SERIAL PRIMARY KEY,
    agent_name  VARCHAR(64) NOT NULL,
    task_key    VARCHAR(16),
    title       TEXT NOT NULL,
    summary     TEXT NOT NULL DEFAULT '',
    body        TEXT NOT NULL DEFAULT '',
    tags        TEXT[] NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_research_agent_created
    ON platform.research_reports (agent_name, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_research_tags
    ON platform.research_reports USING GIN (tags);

CREATE INDEX IF NOT EXISTS idx_research_fts
    ON platform.research_reports USING GIN (
        to_tsvector('english', title || ' ' || summary)
    );

-- Seed platform config values
INSERT INTO platform.config (key, value, description) VALUES
    ('memory.trigger_keywords', 'remember,note,save,store,keep in mind', 'Keywords that trigger automatic memory storage'),
    ('heartbeat.interval_seconds', '60', 'Heartbeat check interval in seconds'),
    ('memory.short_term_days', '30', 'Days to retain short-term memories'),
    ('conversations.retention_days', '30', 'Days to retain conversation history')
ON CONFLICT (key) DO NOTHING;

-- migrate:down

DROP TABLE IF EXISTS platform.research_reports;
DROP TABLE IF EXISTS platform.memories;
DROP TABLE IF EXISTS platform.conversations;
DELETE FROM platform.config WHERE key IN (
    'memory.trigger_keywords',
    'heartbeat.interval_seconds',
    'memory.short_term_days',
    'conversations.retention_days'
);
DROP EXTENSION IF EXISTS vector;
