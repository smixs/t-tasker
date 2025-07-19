# TaskerBot Development Checklist

This checklist contains detailed micro-tasks for developing the TaskerBot project. Mark tasks as completed as you progress through development.

## Quick Stats
- Total tasks: ~150
- Estimated time: 6 weeks
- Current progress: ~70%
- Last updated: 2025-01-19
- Test coverage: 84% (51 tests passing + Deepgram tests ready)
- Core functionality: ✅ Text → Task pipeline working
- Voice functionality: ✅ Voice → Text → Task pipeline working
- Auth flow: ✅ /setup command with token storage working
- Todoist integration: ✅ Full API client with rate limiting
- Deepgram integration: ✅ Voice transcription with auto language detection

## Week 1: Project Setup & Basic Bot Structure

### Day 1-2: Environment & Project Structure
- [x] Install Python 3.12 if not already installed
- [x] Install uv package manager: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [x] Create project directory: `mkdir t-tasker && cd t-tasker`
- [x] Initialize project with uv: `uv init`
- [x] Create virtual environment: `uv venv`
- [x] Create project structure:
  ```
  mkdir -p src/{core,handlers,services,models}
  touch src/__init__.py
  touch src/{core,handlers,services,models}/__init__.py
  ```
- [x] Create base files:
  ```
  touch Dockerfile docker-compose.yml .gitignore
  touch tests/__init__.py
  ```
- [x] Initialize git repository: `git init`
- [x] Create .gitignore with Python template
- [x] Add core dependencies to pyproject.toml:
  - [x] `uv add aiogram==3.21.0`
  - [x] `uv add pydantic==2.10.4`
  - [x] `uv add pydantic-settings==2.7.0`
  - [x] `uv add python-dotenv==1.0.1`
- [x] Add dev dependencies:
  - [x] `uv add --dev ruff==0.8.6`
  - [x] `uv add --dev mypy==1.14.1`
  - [x] `uv add --dev pytest==8.3.4`
  - [x] `uv add --dev pytest-asyncio==0.25.2`
  - [x] `uv add --dev pytest-cov==6.0.0`
- [x] Configure ruff in pyproject.toml:
  ```toml
  [tool.ruff]
  line-length = 120
  target-version = "py312"
  select = ["E", "F", "I", "N", "W", "UP", "B", "SIM", "ASYNC"]
  ```
- [x] Configure mypy in pyproject.toml:
  ```toml
  [tool.mypy]
  python_version = "3.12"
  strict = true
  warn_return_any = true
  warn_unused_configs = true
  ```
- [x] Configure pytest in pyproject.toml:
  ```toml
  [tool.pytest.ini_options]
  asyncio_mode = "auto"
  testpaths = ["tests"]
  ```
- [x] Verify setup: `uv run ruff check src/` (should pass on empty files)
- [x] Verify mypy: `uv run mypy src/` (should pass on empty files)
- [x] Create initial commit: `git add . && git commit -m "Initial project structure"`

### Day 3: Settings & Configuration
- [x] Create `src/core/settings.py`
- [x] Import required modules:
  - [x] `from pydantic_settings import BaseSettings, SettingsConfigDict`
  - [x] `from pydantic import Field, field_validator`
  - [x] `from typing import Optional`
  - [x] `import os`
  - [x] `from pathlib import Path`
- [x] Create Settings class with groups:
  - [x] Telegram settings:
    - [x] `telegram_bot_token: str`
    - [ ] `telegram_bot_token_file: Optional[Path]`
    - [x] `telegram_webhook_url: str`
    - [x] `telegram_webhook_secret: str`
  - [x] OpenAI settings:
    - [x] `openai_api_key: str`
    - [ ] `openai_api_key_file: Optional[Path]`
    - [x] `openai_model: str = "gpt-4o-2024-11-20"`
    - [x] `openai_max_retries: int = 3`
    - [x] `openai_timeout: int = 30`
  - [x] Deepgram settings:
    - [x] `deepgram_api_key: str`
    - [ ] `deepgram_api_key_file: Optional[Path]`
    - [x] `deepgram_model: str = "nova-3"`
    - [x] Auto language detection (no language param)
  - [x] App settings:
    - [x] `app_env: str = "development"`
    - [x] `app_debug: bool = False`
    - [x] `app_port: int = 8443`
    - [x] `metrics_port: int = 8000`
- [ ] Implement file reading for Docker secrets:
  - [ ] Create `read_secret_file` method
  - [ ] Add validators for `*_file` fields
- [x] Add model_config with env prefix and case sensitivity
- [x] Create settings instance singleton pattern
- [x] Write tests for Settings class:
  - [x] Test env var reading
  - [ ] Test file secret reading
  - [x] Test validation errors
  - [x] Test default values
- [x] Run tests: `uv run pytest tests/core/test_settings.py -v`

### Day 4: Bot Setup & Webhook
- [x] Create `src/main.py`
- [x] Add async main function with proper logging setup
- [x] Create `src/core/bot.py`:
  - [x] Initialize Bot instance with settings
  - [x] Initialize Dispatcher
  - [x] Create webhook setup function
  - [x] Create webhook removal function
- [x] Add aiohttp dependency: `uv add aiohttp==3.11.13`
- [x] Create `src/core/server.py`:
  - [x] Create aiohttp.Application
  - [x] Add webhook endpoint `/webhook/{token}`
  - [x] Add health check endpoint `/health`
  - [x] Add metrics placeholder endpoint `/metrics`
  - [x] Implement proper error handling
- [x] Create `src/core/middleware.py`:
  - [x] Create logging middleware
  - [x] Create error handling middleware
  - [x] Create request ID middleware
- [x] Update main.py:
  - [x] Start web server on configured ports
  - [x] Setup webhook on startup
  - [x] Remove webhook on shutdown
  - [x] Implement graceful shutdown
- [x] Test webhook locally with ngrok:
  - [x] Document ngrok setup in README
  - [x] Test webhook registration
  - [x] Test health endpoint

### Day 5: Basic Commands
- [x] Create `src/handlers/commands.py`
- [x] Create command router using aiogram.Router
- [x] Implement `/start` command:
  - [x] Create welcome message
  - [x] Add inline keyboard with "Authorize" button
  - [x] Handle user first interaction
- [x] Implement `/help` command:
  - [x] Create help text with examples
  - [x] Format with Markdown
  - [x] Include all available commands
- [x] Create `src/handlers/__init__.py`:
  - [x] Import all routers
  - [x] Create register_handlers function
- [x] Register handlers in main dispatcher
- [x] Write tests for commands:
  - [x] Mock telegram types
  - [x] Test command responses
  - [ ] Test keyboard generation
- [x] Test bot with BotFather token

## Week 2: AI Integration & Docker

### Day 6-7: OpenAI & Instructor Setup
- [x] Add OpenAI dependencies:
  - [ ] `uv add openai==1.59.4`
  - [x] `uv add instructor==1.7.2`
- [x] Create `src/services/openai_service.py`:
  - [x] Initialize OpenAI client with settings
  - [x] Apply instructor patch
  - [x] Create parse_task method
  - [x] Implement retry logic with exponential backoff
  - [x] Add timeout handling
- [x] Create `src/models/task.py`:
  - [x] Define TaskSchema with Pydantic:
    - [x] `content: str` with validation
    - [x] `description: Optional[str]`
    - [x] `due_string: Optional[str]`
    - [x] `priority: Optional[int]` with Field(ge=1, le=4)
    - [x] `project_name: Optional[str]`
    - [x] `labels: Optional[List[str]]`
    - [x] `recurrence: Optional[str]`
    - [x] `duration: Optional[int]` (in minutes)
  - [x] Add field validators
  - [x] Add model examples
- [x] Create `src/core/exceptions.py`:
  - [x] Define base BotError
  - [x] Define OpenAIError
  - [x] Define ValidationError
  - [x] Define RateLimitError
- [x] Implement profanity filter:
  - [x] Add better-profanity: `uv add better-profanity==0.7.0`
  - [x] Create filter function
  - [x] Apply before OpenAI calls
- [x] Write comprehensive tests:
  - [x] Mock OpenAI responses
  - [x] Test retry logic
  - [x] Test profanity filter
  - [x] Test schema validation

### Day 8: Text Message Handler
- [x] Create `src/handlers/messages.py`
- [x] Create message router
- [x] Implement text message handler:
  - [x] Filter for text messages only
  - [x] Call OpenAI service
  - [x] Handle parsing errors
  - [x] Send formatted response
- [x] Create `src/utils/formatters.py`:
  - [x] Create task_to_telegram_html function
  - [x] Handle None values properly
  - [x] Format dates nicely
  - [x] Add emoji indicators
- [x] Implement typing action:
  - [x] Show "typing..." while processing
  - [x] Handle long operations
- [x] Add rate limiting per user:
  - [x] Track message counts in memory
  - [x] Return rate limit errors
- [ ] Test end-to-end flow:
  - [ ] Send various task formats
  - [ ] Test error messages
  - [ ] Test rate limiting

### Day 9-10: Docker Setup
- [ ] Create multi-stage Dockerfile:
  - [ ] Stage 1 - Builder:
    - [ ] FROM python:3.12-slim as builder
    - [ ] Install uv
    - [ ] Copy pyproject.toml and uv.lock
    - [ ] Install dependencies with uv
  - [ ] Stage 2 - Runtime:
    - [ ] FROM python:3.12-slim
    - [ ] Create appuser (non-root)
    - [ ] Copy site-packages from builder
    - [ ] Copy source code
    - [ ] Set up healthcheck
    - [ ] Expose ports 8443, 8000
- [ ] Create docker-compose.yml:
  - [ ] Define bot service
  - [ ] Add PostgreSQL service
  - [ ] Add Redis service
  - [ ] Configure networks
  - [ ] Add volume mounts
  - [ ] Set up env_file
- [ ] Create .dockerignore
- [ ] Add docker-compose.override.yml for local dev
- [ ] Test Docker build:
  - [ ] Build image
  - [ ] Check image size (<120MB)
  - [ ] Run container
  - [ ] Test health endpoint

## Week 3: Voice Processing & Todoist

### Day 11-12: Chain of Responsibility
- [ ] Create `src/core/processors.py`:
  - [ ] Define ProcessorResult enum (Handled, Skip, Error)
  - [ ] Create abstract MessageProcessor
  - [ ] Define process method signature
- [ ] Create `src/processors/command_processor.py`:
  - [ ] Inherit from MessageProcessor
  - [ ] Check if message is command
  - [ ] Return Skip if not command
- [ ] Create `src/processors/voice_processor.py`:
  - [ ] Check for voice/video/audio
  - [ ] Download file if present
  - [ ] Pass to transcription
  - [ ] Return transcribed text
- [ ] Create `src/processors/text_processor.py`:
  - [ ] Process final text
  - [ ] Call OpenAI service
  - [ ] Create task in Todoist
- [ ] Create processor chain manager:
  - [ ] Register processors in order
  - [ ] Execute chain
  - [ ] Handle errors properly
- [ ] Write unit tests for each processor
- [ ] Test full chain integration

### Day 13: Deepgram Integration
- [x] Add Deepgram SDK: `uv add deepgram-sdk==3.10.1`
- [x] Create `src/services/deepgram_service.py`:
  - [x] Initialize Deepgram client (using httpx instead of SDK)
  - [x] Create transcribe_audio method
  - [x] Handle different audio formats (via mime_type param)
  - [x] Add language detection (auto-detection by not specifying language)
  - [x] Implement timeout handling
- [ ] Create `src/services/transcription.py`:
  - [ ] Define abstract transcriber
  - [ ] Implement Deepgram transcriber
  - [ ] Add error handling
- [x] Update voice processor:
  - [x] Download telegram file
  - [x] No conversion needed (Deepgram handles OGG)
  - [x] Call transcription service
  - [x] Handle errors gracefully
- [ ] Add ffmpeg to Docker image (for future use)
- [x] Test with various audio formats:
  - [x] Voice notes (OGG) - handled by voice_handler
  - [ ] Video notes (MP4)
  - [ ] Audio files (MP3, WAV)

### Day 14: Whisper Fallback
- [ ] Add faster-whisper: `uv add faster-whisper==1.1.0`
- [ ] Create `src/services/whisper_service.py`:
  - [ ] Load model on startup
  - [ ] Implement transcribe method
  - [ ] Add model caching
  - [ ] Handle device selection (CPU/CUDA)
- [ ] Update transcription service:
  - [ ] Add fallback logic
  - [ ] Try Deepgram first
  - [ ] Fall back to Whisper on error
  - [ ] Log fallback usage
- [ ] Add model download to Docker:
  - [ ] Download during build
  - [ ] Cache in volume
- [ ] Test fallback scenarios:
  - [ ] Deepgram API error
  - [ ] Network timeout
  - [ ] Invalid API key

### Day 15: Todoist Client
- [x] Add httpx: `uv add httpx==0.28.1`
- [x] Create `src/services/todoist_service.py`:
  - [x] Create async HTTP client
  - [x] Implement Personal Token validation
  - [x] Implement create_task method
  - [x] Add get_projects method
  - [x] Add get_labels method
- [x] Create `src/core/rate_limiter.py` (integrated in TodoistService):
  - [x] Implement token bucket algorithm
  - [x] 450 requests per 15 minutes (conservative limit)
  - [x] Per-user tracking
  - [ ] Add Redis backend later
- [x] Add Todoist exceptions:
  - [x] TodoistError
  - [x] QuotaExceededError
  - [x] InvalidTokenError
- [x] Test with mock Todoist API:
  - [x] Create mock responses
  - [x] Test rate limiting
  - [ ] Test error handling (partially done)

## Week 4: Database & User Management

### Day 16-17: Database Setup
- [x] Add database dependencies:
  - [x] `uv add asyncpg==0.30.0`
  - [x] `uv add sqlalchemy==2.0.37`
  - [x] `uv add alembic==1.14.0`
- [x] Create `src/models/database.py`:
  - [x] Define User model:
    - [x] id: BigInt primary key (using telegram id)
    - [ ] telegram_user_id: BigInt unique
    - [x] telegram_username: String optional
    - [x] todoist_api_token: Text (encrypted)
    - [x] default_project: String optional
    - [x] language: String default='ru'
    - [x] created_at: DateTime
    - [x] updated_at: DateTime
    - [ ] is_active: Boolean
    - [x] task_count: Integer default=0
  - [x] Create database session manager
  - [x] Add connection pool config
- [x] Create `src/services/encryption.py`:
  - [x] Use cryptography library
  - [x] Implement encrypt method
  - [x] Implement decrypt method
  - [x] Use Fernet symmetric encryption
- [ ] Set up Alembic:
  - [ ] Initialize alembic
  - [ ] Create first migration
  - [ ] Add migration to startup
- [x] Create `src/repositories/user.py`:
  - [x] Create get_by_id
  - [x] Create create_or_update
  - [x] Create delete
  - [x] Add transaction handling

### Day 18: Personal API Token Setup
- [x] Create `/setup` command handler:
  - [x] Send instructions with link to Todoist API token page
  - [x] Include step-by-step guide with screenshots
  - [x] Wait for user to send token
- [ ] Create token validation:
  - [ ] Test token with Todoist API
  - [ ] Check if token is valid
  - [ ] Return user info and available projects
- [x] Update /start command:
  - [x] Check if user has token in DB
  - [x] If not, redirect to /setup
  - [x] If yes, show main menu
- [x] Create `src/middleware/auth.py`:
  - [x] Check user in database
  - [x] Decrypt token if exists
  - [x] Add to context
  - [x] Handle unauthorized users
- [x] Add token management commands:
  - [x] `/setup` - add/update token
  - [x] `/status` - check connection status
  - [x] `/cancel` - cancel current operation
  - [ ] `/revoke` - remove token
  - [ ] `/test` - test current token
- [x] Test token flow (READY TO TEST):
  - [ ] Test token validation with real Todoist API
  - [x] Test token storage in database
  - [x] Test middleware auth flow

### Day 19: User Commands
- [ ] Implement `/settings` command:
  - [ ] Show current status
  - [ ] Add "Revoke access" button
  - [ ] Add "Change language" option
  - [ ] Handle button callbacks
- [ ] Implement `/limits` command:
  - [ ] Call Todoist Sync API
  - [ ] Parse quota information
  - [ ] Format nicely for user
  - [ ] Cache for 5 minutes
- [ ] Implement `/usage` command:
  - [ ] Add task_count to User model
  - [ ] Increment on each task
  - [ ] Show daily/weekly/monthly stats
  - [ ] Add reset functionality
- [ ] Implement `/delete_my_data`:
  - [ ] Confirm with user
  - [ ] Delete from database
  - [ ] Revoke Todoist token
  - [ ] Send confirmation

### Day 20: Caching Layer
- [ ] Add Redis dependency: `uv add redis==5.3.0`
- [ ] Create `src/core/cache.py`:
  - [ ] Create Redis connection pool
  - [ ] Implement get/set methods
  - [ ] Add TTL support
  - [ ] Add JSON serialization
- [ ] Cache Todoist data:
  - [ ] Projects (5 min TTL)
  - [ ] Labels (5 min TTL)
  - [ ] User quotas (5 min TTL)
- [ ] Add cache warming:
  - [ ] On user authorization
  - [ ] On cache miss
- [ ] Add cache invalidation:
  - [ ] On project creation
  - [ ] On settings change
- [ ] Test caching layer:
  - [ ] Test TTL expiration
  - [ ] Test concurrent access
  - [ ] Test serialization

## Week 5: Monitoring & Error Handling

### Day 21-22: Error Handling
- [ ] Create `src/handlers/errors.py`:
  - [ ] Create error router
  - [ ] Handle BotError types
  - [ ] Handle unexpected errors
  - [ ] Send user-friendly messages
- [ ] Add error types:
  - [ ] TranscriptionError
  - [ ] TodoistQuotaError
  - [ ] OpenAIRateLimitError
  - [ ] ValidationError
- [ ] Create error messages:
  - [ ] Multi-language support
  - [ ] Helpful suggestions
  - [ ] Retry instructions
- [ ] Implement circuit breaker:
  - [ ] For external services
  - [ ] Auto-recovery
  - [ ] Fallback behavior
- [ ] Test error scenarios:
  - [ ] Service timeouts
  - [ ] Invalid inputs
  - [ ] Rate limits

### Day 23: Sentry Integration
- [ ] Add Sentry SDK: `uv add sentry-sdk==2.20.0`
- [ ] Configure Sentry in settings
- [ ] Initialize in main.py:
  - [ ] Set environment
  - [ ] Set release version
  - [ ] Configure sampling
- [ ] Add custom context:
  - [ ] User ID
  - [ ] Message type
  - [ ] Processing time
- [ ] Create custom fingerprints:
  - [ ] Group similar errors
  - [ ] Ignore known issues
- [ ] Test Sentry integration:
  - [ ] Trigger test error
  - [ ] Check dashboard
  - [ ] Verify grouping

### Day 24: OpenTelemetry
- [ ] Add OTEL dependencies:
  - [ ] `uv add opentelemetry-api==1.29.0`
  - [ ] `uv add opentelemetry-sdk==1.29.0`
  - [ ] `uv add opentelemetry-instrumentation==0.50.0`
- [ ] Configure OTEL:
  - [ ] Set up trace provider
  - [ ] Configure OTLP exporter
  - [ ] Set service name
- [ ] Instrument components:
  - [ ] HTTP clients (httpx)
  - [ ] Database queries
  - [ ] Redis operations
  - [ ] Message processing
- [ ] Add custom spans:
  - [ ] Task parsing
  - [ ] Transcription
  - [ ] Todoist API calls
- [ ] Add span attributes:
  - [ ] User ID
  - [ ] Message type
  - [ ] Processing result

### Day 25: Prometheus Metrics
- [ ] Add prometheus client: `uv add prometheus-client==0.21.1`
- [ ] Create `src/core/metrics.py`:
  - [ ] Define counter metrics:
    - [ ] messages_total
    - [ ] tasks_created_total
    - [ ] errors_total
  - [ ] Define histogram metrics:
    - [ ] processing_duration
    - [ ] api_call_duration
  - [ ] Define gauge metrics:
    - [ ] active_users
    - [ ] cache_hit_ratio
- [ ] Add metrics endpoint:
  - [ ] Expose on /metrics
  - [ ] Format for Prometheus
- [ ] Instrument code:
  - [ ] Message handlers
  - [ ] API calls
  - [ ] Cache operations
- [ ] Create Grafana dashboards:
  - [ ] Service overview
  - [ ] User activity
  - [ ] Error rates
  - [ ] Performance metrics

## Week 6: Production Readiness

### Day 26-27: Comprehensive Testing
- [ ] Unit tests completion:
  - [ ] 90% coverage target
  - [ ] All services tested
  - [ ] All handlers tested
  - [ ] Mock all externals
- [ ] Integration tests:
  - [ ] Database operations
  - [ ] Redis operations
  - [ ] Full message flow
- [ ] Load testing:
  - [ ] Use locust
  - [ ] Test 1000 concurrent users
  - [ ] Measure latencies
  - [ ] Find bottlenecks
- [ ] Security testing:
  - [ ] Input validation
  - [ ] SQL injection
  - [ ] Token security
  - [ ] Rate limiting

### Day 28: CI/CD Pipeline
- [ ] Create `.github/workflows/ci.yml`:
  - [ ] Run on PR and push
  - [ ] Set up Python 3.12
  - [ ] Install uv
  - [ ] Run linters
  - [ ] Run tests
  - [ ] Upload coverage
- [ ] Create `.github/workflows/cd.yml`:
  - [ ] Build Docker image
  - [ ] Push to registry
  - [ ] Deploy to staging
  - [ ] Run smoke tests
  - [ ] Deploy to production
- [ ] Add security scanning:
  - [ ] Dependency scanning
  - [ ] Container scanning
  - [ ] Secret scanning

### Day 29: Documentation
- [ ] Complete README.md:
  - [ ] Project overview
  - [ ] Quick start guide
  - [ ] Configuration
  - [ ] Deployment guide
- [ ] API documentation:
  - [ ] Document all endpoints
  - [ ] Add examples
  - [ ] Error responses
- [ ] Create CONTRIBUTING.md
- [ ] Create SECURITY.md
- [ ] Add inline code documentation

### Day 30: Production Deployment
- [ ] Finalize Docker image:
  - [ ] Minimize size
  - [ ] Security hardening
  - [ ] Health checks
- [ ] Create Kubernetes manifests:
  - [ ] Deployment
  - [ ] Service
  - [ ] ConfigMap
  - [ ] Secrets
  - [ ] HPA
- [ ] Set up monitoring:
  - [ ] Prometheus
  - [ ] Grafana
  - [ ] Alerts
- [ ] Performance tuning:
  - [ ] Database indexes
  - [ ] Connection pools
  - [ ] Cache optimization
- [ ] Final checklist:
  - [ ] All tests passing
  - [ ] Documentation complete
  - [ ] Monitoring active
  - [ ] Backups configured
  - [ ] Incident response plan

## Completed Improvements (2025-01-19)

### Fixed Issues
- [x] PostgreSQL connection error with Docker
  - [x] Created Makefile for easier Docker management
  - [x] Fixed DATABASE_URL environment variable conflicts
  - [x] Added `make run` command with proper env handling
- [x] Database overflow error for large Telegram IDs
  - [x] Changed user ID columns from Integer to BigInteger
  - [x] Updated both User and Task models
- [x] Authentication flow infinite loop
  - [x] Fixed AuthMiddleware to allow messages during setup
  - [x] Added FSM state checking for token processing
  - [x] Created separate states.py module

### Infrastructure Improvements
- [x] Created comprehensive Makefile with commands:
  - [x] `make run` - Run bot with correct DATABASE_URL
  - [x] `make restart` - Full Docker restart with clean DB
  - [x] `make logs` - View container logs
  - [x] `make status` - Check container status
  - [x] `make test` - Run tests
  - [x] `make lint` - Run linter
  - [x] `make typecheck` - Run type checker

## Additional Features for Agencies

### Quick Commands & Templates
- [ ] Implement quick commands:
  - [ ] `/t` - create task for today
  - [ ] `/tm` - create task for tomorrow
  - [ ] `/urgent` - create high priority task
  - [ ] `/meeting [client]` - create meeting task with template
- [ ] Add project shortcuts:
  - [ ] Auto-complete for frequent projects
  - [ ] Last 5 used projects in quick menu
  - [ ] Default project setting per user
- [ ] Create task templates:
  - [ ] Client call template
  - [ ] Meeting notes template
  - [ ] Review/feedback template
  - [ ] Report deadline template

### Voice Enhancements
- [ ] Improve voice recognition for business context:
  - [ ] Client name detection
  - [ ] Project keyword mapping
  - [ ] Deadline parsing ("end of week", "next Monday")
- [ ] Add voice feedback:
  - [ ] Confirmation message after task creation
  - [ ] Voice note summary in text
- [ ] Multi-language support:
  - [ ] Russian language for Deepgram
  - [ ] Language auto-detection
  - [ ] Per-user language preference

### Team Features
- [ ] Basic team statistics:
  - [ ] Daily task count
  - [ ] Weekly summary
  - [ ] Most active projects
- [ ] Shared project templates:
  - [ ] Agency-specific project list
  - [ ] Common labels (billable, internal, urgent)
  - [ ] Standard priority mappings

## Post-Launch Tasks

### Maintenance & Improvements
- [ ] Set up on-call rotation
- [ ] Create runbook for common issues
- [ ] Plan for feature additions:
  - [ ] Multiple language support
  - [ ] Voice response messages
  - [ ] Task templates
  - [ ] Bulk operations
- [ ] Performance optimization:
  - [ ] Database query optimization
  - [ ] Caching strategy review
  - [ ] API call batching
- [ ] User feedback implementation:
  - [ ] Feature requests
  - [ ] Bug fixes
  - [ ] UX improvements

## Notes

- Always run tests after implementing features
- Update this checklist when discovering new tasks
- Check dependencies for security updates weekly
- Monitor error rates and performance daily
- Keep documentation in sync with code