FROM python:3.12-slim

WORKDIR /opt/inotagent-trading

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install deps first (cache layer)
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --frozen 2>/dev/null || uv sync --no-dev

# Copy source
COPY . .

CMD ["python", "-m", "poller.public"]
