.PHONY: help restart rebuild logs shell test

# Default - show help
help:
	@echo "TaskerBot Commands:"
	@echo ""
	@echo "  make restart  - Update code and restart bot (keeps databases)"
	@echo "  make rebuild  - Full clean rebuild (removes everything including databases)"
	@echo "  make logs     - Show bot logs"
	@echo "  make shell    - Shell into bot container"
	@echo "  make test     - Run tests"

# Update code and restart bot (keeps databases)
restart:
	@echo "Restarting bot with new code..."
	docker compose down bot
	@find src -name "*.py" -exec touch {} \;
	CACHEBUST=$$(date +%s) docker compose build --build-arg CACHEBUST=$$(date +%s) bot
	docker compose up -d bot
	docker compose logs -f bot

# Full clean rebuild (removes everything including databases)
rebuild:
	@echo "Full rebuild - removing everything..."
	docker compose down -v
	docker volume prune -f
	docker rmi t-tasker-bot || true
	docker compose build --no-cache bot
	docker compose up -d
	docker compose logs -f bot

# Show bot logs
logs:
	docker compose logs -f bot

# Shell into bot container
shell:
	docker compose exec bot bash

# Run tests
test:
	uv run pytest