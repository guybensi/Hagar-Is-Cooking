FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1

# Install dependencies first (separate layer, cached unless pyproject.toml/uv.lock change).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Then copy the actual source and install the project itself.
# README.md is required at this step -- pyproject.toml's readme field points hatchling at it.
COPY app ./app
COPY README.md ./
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:${PATH}"

CMD ["python", "-m", "app"]
