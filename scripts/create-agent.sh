#!/bin/bash
# Create a new agent from the _template folder
# Usage: ./scripts/create-agent.sh <agent_name> [--email GIT_EMAIL]

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEMPLATE_DIR="${REPO_ROOT}/agents/_template"
COMPOSE="${REPO_ROOT}/docker-compose.yml"

# --- Parse args ---
NAME=""
GIT_EMAIL=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --email) GIT_EMAIL="$2"; shift 2;;
        -*) echo "Unknown option: $1"; exit 1;;
        *) NAME="$1"; shift;;
    esac
done

if [ -z "$NAME" ]; then
    cat <<EOF
Create a new agent from template

Usage: ./scripts/create-agent.sh <agent_name> [--email GIT_EMAIL]

Options:
  --email EMAIL    Git email for the agent (default: <name>@inotives.ai)

Examples:
  ./scripts/create-agent.sh kai
  ./scripts/create-agent.sh kai --email kai.bot@gmail.com

What this does:
  1. Copies agents/_template/ to agents/<name>/
  2. Replaces all {{PLACEHOLDER}} tokens in the new files
  3. Generates agents/<name>/.env from .env.template
  4. Adds the service + volume to docker-compose.yml

After running, you need to:
  1. Edit agents/<name>/.env with API keys and Discord bot token
  2. Edit agents/<name>/AGENTS.md to define the agent's role and personality
  3. Edit agents/<name>/agent.yml to set model, fallbacks, and mission_tags
  4. Run: make deploy AGENT=<name>
EOF
    exit 1
fi

# --- Validate ---
NAME_LOWER=$(echo "$NAME" | tr '[:upper:]' '[:lower:]')
AGENT_DIR="${REPO_ROOT}/agents/${NAME_LOWER}"

if [ -d "$AGENT_DIR" ]; then
    echo "Error: Agent directory already exists: agents/${NAME_LOWER}/"
    exit 1
fi

if [ ! -d "$TEMPLATE_DIR" ]; then
    echo "Error: Template directory not found: agents/_template/"
    exit 1
fi

if [ -z "$GIT_EMAIL" ]; then
    GIT_EMAIL="${NAME_LOWER}@inotives.ai"
fi

# Capitalize first letter for display name
NAME_DISPLAY="$(echo "${NAME_LOWER:0:1}" | tr '[:lower:]' '[:upper:]')${NAME_LOWER:1}"

echo "Creating agent '${NAME_LOWER}'..."

# --- Step 1: Copy template ---
cp -r "$TEMPLATE_DIR" "$AGENT_DIR"
echo "  Copied template to agents/${NAME_LOWER}/"

# --- Step 2: Replace placeholders ---
for file in "$AGENT_DIR"/*; do
    [ -f "$file" ] || continue
    sed -i '' \
        -e "s/{{AGENT_NAME}}/${NAME_DISPLAY}/g" \
        -e "s/{{AGENT_NAME_LOWER}}/${NAME_LOWER}/g" \
        -e "s/{{EMOJI}}/🤖/g" \
        -e "s/{{PERSONALITY_LINE_1}}/Describe personality trait 1/g" \
        -e "s/{{PERSONALITY_LINE_2}}/Describe personality trait 2/g" \
        -e "s/{{ROLE_DESCRIPTION}}/Describe the agent's role and responsibilities./g" \
        -e "s/{{DISCORD_OWNER_ID}}/YOUR_DISCORD_USER_ID/g" \
        -e "s/{{DISCORD_GUILD_ID}}/YOUR_DISCORD_GUILD_ID/g" \
        -e "s/{{TELEGRAM_USER_ID}}/YOUR_TELEGRAM_USER_ID/g" \
        "$file"
done
echo "  Replaced placeholders"

# --- Step 3: Generate .env from template ---
cp "$AGENT_DIR/.env.template" "$AGENT_DIR/.env"
echo "  Generated .env (fill in API keys and Discord token)"

# --- Step 4: Add service + volume to docker-compose.yml ---
if grep -q "^  ${NAME_LOWER}:" "$COMPOSE"; then
    echo "  Service '${NAME_LOWER}' already exists in docker-compose.yml, skipping"
else
    python3 -c "
import sys

name = '${NAME_LOWER}'
email = '${GIT_EMAIL}'

service = '''
  {name}:
    build:
      context: .
      dockerfile: agents/{name}/Dockerfile
    container_name: agent_{name}
    env_file:
      - .env
      - agents/{name}/.env
    environment:
      AGENT_NAME: {name}
      GIT_EMAIL: {email}
      PLATFORM_SCHEMA: \${{PLATFORM_SCHEMA:-platform}}
      POSTGRES_HOST: \${{POSTGRES_HOST:-postgres}}
      POSTGRES_PORT: \${{INTERNAL_POSTGRES_PORT:-5432}}
    volumes:
      - {name}_workspace:/workspace
    depends_on:
      postgres:
        condition: service_healthy
        required: false
    networks:
      - platform
    healthcheck:
      test: [\"CMD-SHELL\", \"kill -0 1\"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    deploy:
      resources:
        limits:
          cpus: \"1.0\"
          memory: 2g
'''.format(name=name, email=email)

with open('$COMPOSE', 'r') as f:
    content = f.read()

# Insert service before 'ui:' service
content = content.replace('\n  ui:\n', service + '\n  ui:\n', 1)

# Add volume before the last line (or after last existing volume)
volume_line = f'  {name}_workspace:'
if volume_line not in content:
    content = content.rstrip() + f'\n  {name}_workspace:\n'

with open('$COMPOSE', 'w') as f:
    f.write(content)
"
    echo "  Added service + volume to docker-compose.yml"
fi

# --- Done ---
echo ""
echo "Agent '${NAME_LOWER}' created successfully!"
echo ""
echo "Next steps:"
echo "  1. Edit agents/${NAME_LOWER}/.env          — add API keys and channel tokens"
echo "  2. Edit agents/${NAME_LOWER}/AGENTS.md      — define role, personality, and workflow"
echo "  3. Edit agents/${NAME_LOWER}/agent.yml      — set model, fallbacks, channels, and mission_tags"
echo "  4. Update allowFrom IDs in agent.yml       — Discord owner ID, Telegram user ID"
echo "  5. Run: make deploy AGENT=${NAME_LOWER}"
