FROM inotagent-base

# Copy agent config
COPY agents/ino/agent.yml /app/agents/ino/agent.yml

# Copy workspace files (loaded by config as system prompt)
COPY agents/ino/AGENTS.md /app/agents/ino/AGENTS.md
COPY agents/ino/TOOLS.md /app/agents/ino/TOOLS.md

# Also put AGENTS.md in workspace for tool context
COPY agents/ino/AGENTS.md /workspace/AGENTS.md

# Scratch directory for temporary scripts and data
RUN mkdir -p /workspace/scratch
