FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -U appuser

# Set working directory
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY src ./src

# Copy assets (images, etc.)
COPY assets ./assets

# Change ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Run the bot
CMD ["uv", "run", "python", "-m", "src.main"]