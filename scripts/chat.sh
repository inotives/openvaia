#!/usr/bin/env bash
# Chat with an agent via inotagent CLI.
# Usage:
#   ./scripts/chat.sh                       # interactive REPL with ino
#   ./scripts/chat.sh robin                 # interactive REPL with robin
#   ./scripts/chat.sh ino "hello there"     # one-shot message to ino
#   ./scripts/chat.sh robin "check tasks"   # one-shot message to robin

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AGENT="${1:-ino}"
AGENT_DIR="$REPO_ROOT/agents/$AGENT"
ENV_FILE="$AGENT_DIR/.env"
MESSAGE="${2:-}"

if [ ! -d "$AGENT_DIR" ]; then
    echo "Error: Agent directory not found: $AGENT_DIR"
    echo "Available agents:"
    ls "$REPO_ROOT/agents/"
    exit 1
fi

# Load agent's .env if it exists
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

cd "$REPO_ROOT/inotagent"
if [ -n "$MESSAGE" ]; then
    exec uv run python -m inotagent.main --agent-dir "$AGENT_DIR" -m "$MESSAGE"
else
    exec uv run python -m inotagent.main --agent-dir "$AGENT_DIR"
fi
