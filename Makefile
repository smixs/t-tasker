.PHONY: help clean db restart run logs status test lint typecheck install \
        docker-build docker-up docker-down docker-logs docker-shell docker-restart \
        docker-rebuild docker-deploy backup-db shell-postgres shell-redis

# Default target
help:
	@echo "TaskerBot Makefile Commands:"
	@echo ""
	@echo "Local Development:"
	@echo "  make clean      - Stop all containers and remove volumes"
	@echo "  make db         - Start PostgreSQL and Redis containers"
	@echo "  make restart    - Full restart with clean database"
	@echo "  make run        - Run bot locally (polling mode)"
	@echo "  make logs       - Show container logs"
	@echo "  make status     - Show container status"
	@echo ""
	@echo "Docker Commands:"
	@echo "  make docker-build    - Build Docker image"
	@echo "  make docker-up       - Start containers (with rebuild)"
	@echo "  make docker-down     - Stop containers"
	@echo "  make docker-restart  - Restart bot (with rebuild)"
	@echo "  make docker-rebuild  - Full rebuild without cache"
	@echo "  make docker-deploy   - Full deploy cycle"
	@echo "  make docker-logs     - Show bot logs"
	@echo "  make docker-shell    - Shell into bot container"
	@echo ""
	@echo "Code Quality:"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linter"
	@echo "  make typecheck  - Run type checker"
	@echo "  make install    - Install dependencies"

# Stop all containers and remove volumes
clean:
	docker compose down -v
	docker compose rm -f
	docker volume prune -f

# Start database containers
db:
	docker compose up -d postgres redis
	@echo "Waiting for containers to be healthy..."
	@sleep 5
	docker compose ps

# Full restart with clean database
restart: clean db

# Run bot locally with correct DATABASE_URL
run:
	@echo "Starting bot in polling mode..."
	@unset DATABASE_URL && DATABASE_URL=postgresql+asyncpg://taskerbot:password@localhost:5432/taskerbot uv run python run_simple.py

# Run bot with webhook (production mode)
run-webhook:
	@echo "Starting bot with webhook..."
	@unset DATABASE_URL && DATABASE_URL=postgresql+asyncpg://taskerbot:password@localhost:5432/taskerbot uv run python src/main.py

# Show container logs
logs:
	docker compose logs -f

# Show only postgres logs
logs-postgres:
	docker compose logs -f postgres

# Show only redis logs
logs-redis:
	docker compose logs -f redis

# Show container status
status:
	docker compose ps

# Run tests
test:
	uv run pytest

# Run tests with coverage
test-cov:
	uv run pytest --cov=src --cov-report=html

# Run linter
lint:
	uv run ruff check src tests

# Fix linting issues
lint-fix:
	uv run ruff check --fix src tests

# Run type checker
typecheck:
	uv run mypy src

# Install dependencies
install:
	uv sync

# Update dependencies
update:
	uv lock --upgrade

# Create database backup
backup-db:
	docker exec taskerbot-postgres pg_dump -U taskerbot taskerbot > backup_$(shell date +%Y%m%d_%H%M%S).sql

# Shell into postgres container
shell-postgres:
	docker exec -it taskerbot-postgres psql -U taskerbot -d taskerbot

# Shell into redis container
shell-redis:
	docker exec -it taskerbot-redis redis-cli

# Remove system DATABASE_URL variable (if set)
unset-env:
	@echo "To remove system DATABASE_URL, run:"
	@echo "unset DATABASE_URL"

# Docker commands
docker-build:
	docker compose build

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f bot

docker-shell:
	docker compose exec bot bash

docker-restart:
	docker compose down
	docker compose up -d --build bot

docker-rebuild:
	docker compose down
	docker compose build --no-cache bot
	docker compose up -d bot

docker-deploy: docker-down docker-build docker-up docker-logs