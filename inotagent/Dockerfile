FROM python:3.12-slim AS base

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl libpq-dev build-essential ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update && apt-get install -y gh && rm -rf /var/lib/apt/lists/*

# dbmate for DB migrations
RUN curl -fsSL -o /usr/local/bin/dbmate \
    https://github.com/amacneil/dbmate/releases/latest/download/dbmate-linux-$(dpkg --print-architecture) \
    && chmod +x /usr/local/bin/dbmate

# uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Python deps
WORKDIR /app
COPY inotagent/pyproject.toml inotagent/uv.lock ./inotagent/
RUN cd inotagent && uv sync --no-dev --frozen --no-install-project
ENV PATH="/app/inotagent/.venv/bin:$PATH"

# Playwright chromium + system deps
RUN playwright install --with-deps chromium

# Copy inotagent source
COPY inotagent/src/ ./inotagent/src/

# Copy config files (models, platform)
COPY inotagent/models.yml inotagent/platform.yml ./inotagent/

# Copy DB migrations
COPY infra/postgres/migrations ./infra/postgres/migrations

# Workspace directory for repos
RUN mkdir -p /workspace/repos

# Copy entrypoint
COPY inotagent/entrypoint.sh /app/inotagent/entrypoint.sh
RUN chmod +x /app/inotagent/entrypoint.sh

ENV WORKSPACE_DIR=/workspace
ENV PYTHONPATH=/app/inotagent/src

CMD ["bash", "/app/inotagent/entrypoint.sh"]
