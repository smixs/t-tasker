FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -U appuser

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Change ownership of the working directory
RUN chown appuser:appuser /app

# Switch to non-root user
USER appuser

# Enable bytecode compilation for better startup performance
ENV UV_COMPILE_BYTECODE=1
# Use copy mode for Docker (required when using cache mounts)
ENV UV_LINK_MODE=copy

# Install dependencies in a separate layer with cache mount
# This significantly speeds up rebuilds when dependencies don't change
COPY --chown=appuser:appuser pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/home/appuser/.cache/uv,uid=1000,gid=1000 \
    uv sync --frozen --no-dev --no-install-project

# Add cache-busting argument  
ARG CACHEBUST=1

# Copy the rest of the project
COPY --chown=appuser:appuser src ./src
COPY --chown=appuser:appuser assets ./assets

# Final sync to install the project itself
RUN --mount=type=cache,target=/home/appuser/.cache/uv,uid=1000,gid=1000 \
    uv sync --frozen --no-dev

# Run the bot
CMD ["uv", "run", "python", "-m", "src.main"]