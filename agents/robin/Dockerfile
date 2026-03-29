FROM inotagent-base

# Copy agent config
COPY agents/robin/agent.yml /app/agents/robin/agent.yml

# Copy workspace files (loaded by config as system prompt)
COPY agents/robin/AGENTS.md /app/agents/robin/AGENTS.md
COPY agents/robin/TOOLS.md /app/agents/robin/TOOLS.md

# Also put AGENTS.md in workspace for tool context
COPY agents/robin/AGENTS.md /workspace/AGENTS.md
