FROM inotagent-base

# Copy agent config
COPY agents/{{AGENT_NAME_LOWER}}/agent.yml /app/agents/{{AGENT_NAME_LOWER}}/agent.yml

# Copy workspace files (loaded by config as system prompt)
COPY agents/{{AGENT_NAME_LOWER}}/AGENTS.md /app/agents/{{AGENT_NAME_LOWER}}/AGENTS.md
COPY agents/{{AGENT_NAME_LOWER}}/TOOLS.md /app/agents/{{AGENT_NAME_LOWER}}/TOOLS.md

# Also put AGENTS.md in workspace for tool context
COPY agents/{{AGENT_NAME_LOWER}}/AGENTS.md /workspace/AGENTS.md

# Scratch directory for temporary scripts and data
RUN mkdir -p /workspace/scratch
