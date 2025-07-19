# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# TaskerBot - Telegram to Todoist Bot

## IMPORTANT: Development Checklist
**ALWAYS check CHECKLIST.md before starting any work!** This file contains ~150 detailed micro-tasks organized by week. You MUST:
1. Read CHECKLIST.md to understand current progress
2. Mark tasks as completed when you finish them
3. Add new subtasks if you discover them during development
4. Never skip tasks - they have dependencies

## Project Context
Production-ready Telegram bot converting text/voice/video to Todoist tasks with <4s latency, multi-user support via personal tokens, 99.8% uptime.

## Architecture Rules
- **Python 3.12** with **uv** package manager (NEVER use pip)
- **aiogram 3.21+** for Telegram (use Router pattern)
- **Instructor Mode.TOOLS** with OpenAI gpt-4o-2024-11-20
- **PostgreSQL + asyncpg** for user data
- **Chain of Responsibility** for message processing

## Code Standards
### File Organization
- `src/handlers/`: Telegram command & message handlers
- `src/services/`: External API clients (Todoist, OpenAI, Deepgram)
- `src/core/`: Settings, exceptions, middleware, base classes
- `src/models/`: Pydantic schemas & SQLAlchemy models
- Keep modules <300 lines, split if larger

### Async Patterns
- Use `async def` for all handlers and services
- Never use blocking I/O, always asyncio alternatives
- Use `asyncio.gather()` for concurrent operations
- Handle cancellation properly with try/finally

### Error Handling
- Custom exceptions in `src/core/exceptions.py`: TranscriptionError, OpenAIError, TodoistError, RateLimitError
- Global error_router catches all, sends user-friendly messages
- Log to Sentry with proper tags
- Never expose internal errors to users

### Testing Requirements
- **TDD approach**: test first, implement second
- Use `pytest-asyncio` for async tests
- Mock external services (OpenAI, Todoist, Deepgram)
- Target 90% coverage on business logic
- Test files mirror source structure in `tests/`

## External Services
### OpenAI Integration
- Always use Instructor with `response_model`
- 3 retries with exponential backoff
- Profanity filter before sending (replace with *)
- Handle rate limits gracefully

### Todoist API
- Rate limit: 450 requests/15 minutes
- Cache projects/labels/plans (5min TTL)
- Each user provides their Personal Token via /setup command
- Tokens are encrypted and stored per-user in database
- Always validate project_name exists before creating tasks

### Speech Recognition
- Primary: Deepgram Nova-3
- Fallback: faster-whisper (auto-switch on errors)
- Max audio duration: 5 minutes
- Support: voice notes, video notes, audio files

## Security & Performance
- Run as non-root user `appuser` in Docker
- Use Docker secrets for sensitive data
- Encrypt Todoist tokens in database
- Target: P95 latency <4s, CPU ≤0.5, RAM ≤512MB
- Health check endpoint on :8000/health

## Development Workflow
1. **FIRST: Check CHECKLIST.md for current progress and next tasks**
2. Check existing tests before modifying code
3. Run `uv run ruff check` and `uv run mypy` before commits
4. Use `uv add` for dependencies, never pip
5. Update CHECKLIST.md when completing tasks or finding new ones
6. Update this file when adding new patterns
7. Docker image must be ≤120MB

## Current Implementation Status
- [x] Basic bot structure with webhook and polling mode
- [x] Settings management with pydantic-settings
- [x] Command handlers (/start, /help, /setup, /undo, /recent, /autodelete)
- [x] OpenAI integration for task parsing (Instructor with Mode.TOOLS)
- [x] Text message processing
- [x] Voice/audio transcription (Deepgram Nova-3 with Russian support)
- [x] Todoist API client with rate limiting
- [x] /setup command for Personal Token input with encryption
- [x] Database models (PostgreSQL + asyncpg)
- [x] Error handling and middleware
- [x] Callback handlers for inline keyboard buttons
- [x] Auto-delete previous task feature
- [ ] Monitoring (Sentry, OTEL, Prometheus)
- [x] Docker setup with multi-stage build
- [ ] CI/CD pipeline

## Environment Variables
See `.env.example` for required configuration. Never commit `.env` files.

## Commands Reference
```bash
# Development
uv run python src/main.py      # Run bot locally
uv run pytest                  # Run tests
uv run pytest tests/specific_test.py::test_function  # Run single test
uv run pytest --cov=src       # Run tests with coverage
uv run ruff check             # Lint code
uv run ruff format            # Format code
uv run mypy src              # Type check

# Docker
docker compose up -d          # Start services
docker compose logs -f bot    # View logs
docker compose down          # Stop services
docker compose exec bot bash  # Shell into container

# Project Management
uv init                       # Initialize new uv project
uv add package_name          # Add production dependency
uv add --dev package_name    # Add development dependency
uv sync                      # Install all dependencies
uv export --format requirements-txt > requirements.txt  # Export deps

# Local Development
ngrok http 8443              # Expose webhook for Telegram
```

## Known Constraints
- Telegram webhook requires HTTPS (use ngrok for local dev)
- Todoist API doesn't support batch operations
- OpenAI structured outputs may fail on complex inputs
- Database migrations not yet implemented

## Development Best Practices
- Если ты в чем-то сомневаешься, всегда используй context7 mcp

## Deepgram Integration Notes

### Nova-3 поддерживает русский язык (2025)
- Используем `model=nova-3`
- Для автодетекта: `detect_language=true`
- НЕ указываем `language` параметр
- Telegram voice = OGG OPUS формат

### Если пустой транскрипт:
1. Проверить размер аудио (не 0)
2. Проверить MIME type: "audio/ogg;codecs=opus"
3. Включить detect_language=true
4. Проверить логи Deepgram response

## Recent Fixes (2025-01-19)

### Callback Handlers Fixed
- **Problem**: Кнопки под задачами выдавали ошибку `missing 2 required positional arguments: 'user' and 'todoist_token'`
- **Solution**: AuthMiddleware теперь обрабатывает CallbackQuery events (src/middleware/auth.py:47-49)
- **Result**: Все кнопки (Готово, Удалить) работают корректно

### Auto-delete Feature Added
- **Command**: `/autodelete` - включает/выключает автоудаление предыдущей задачи
- **Database**: Добавлено поле `auto_delete_previous` в модель User
- **Logic**: При создании новой задачи проверяется настройка и удаляется предыдущая
- **Works for**: Текстовые и голосовые сообщения

### Docker Build Process
- **Important**: Используй `make docker-build` для обновления кода
- **Wrong**: `make docker-restart` только перезапускает контейнер со старым кодом
- **After DB changes**: Всегда перезапускай бота после миграций