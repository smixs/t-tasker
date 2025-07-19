# TaskerBot Development Checklist

This checklist contains detailed micro-tasks for developing the TaskerBot project. Mark tasks as completed as you progress through development.

## Quick Stats
- Total tasks: ~150
- Estimated time: 6 weeks
- Current progress: 0%

## Week 1: Project Setup & Basic Bot Structure

### Day 1-2: Environment & Project Structure
- [ ] Install Python 3.12 if not already installed
- [ ] Install uv package manager: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [ ] Create project directory: `mkdir t-tasker && cd t-tasker`
- [ ] Initialize project with uv: `uv init`
- [ ] Create virtual environment: `uv venv`
- [ ] Create project structure:
  ```
  mkdir -p src/{core,handlers,services,models}
  touch src/__init__.py
  touch src/{core,handlers,services,models}/__init__.py
  ```
- [ ] Create base files:
  ```
  touch Dockerfile docker-compose.yml .gitignore
  touch tests/__init__.py
  ```
- [ ] Initialize git repository: `git init`
- [ ] Create .gitignore with Python template
- [ ] Add core dependencies to pyproject.toml:
  - [ ] `uv add aiogram==3.21.0`
  - [ ] `uv add pydantic==2.10.4`
  - [ ] `uv add pydantic-settings==2.7.0`
  - [ ] `uv add python-dotenv==1.0.1`
- [ ] Add dev dependencies:
  - [ ] `uv add --dev ruff==0.8.6`
  - [ ] `uv add --dev mypy==1.14.1`
  - [ ] `uv add --dev pytest==8.3.4`
  - [ ] `uv add --dev pytest-asyncio==0.25.2`
  - [ ] `uv add --dev pytest-cov==6.0.0`
- [ ] Configure ruff in pyproject.toml:
  ```toml
  [tool.ruff]
  line-length = 120
  target-version = "py312"
  select = ["E", "F", "I", "N", "W", "UP", "B", "SIM", "ASYNC"]
  ```
- [ ] Configure mypy in pyproject.toml:
  ```toml
  [tool.mypy]
  python_version = "3.12"
  strict = true
  warn_return_any = true
  warn_unused_configs = true
  ```
- [ ] Configure pytest in pyproject.toml:
  ```toml
  [tool.pytest.ini_options]
  asyncio_mode = "auto"
  testpaths = ["tests"]
  ```
- [ ] Verify setup: `uv run ruff check src/` (should pass on empty files)
- [ ] Verify mypy: `uv run mypy src/` (should pass on empty files)
- [ ] Create initial commit: `git add . && git commit -m "Initial project structure"`

### Day 3: Settings & Configuration
- [ ] Create `src/core/settings.py`
- [ ] Import required modules:
  - [ ] `from pydantic_settings import BaseSettings, SettingsConfigDict`
  - [ ] `from pydantic import Field, field_validator`
  - [ ] `from typing import Optional`
  - [ ] `import os`
  - [ ] `from pathlib import Path`
- [ ] Create Settings class with groups:
  - [ ] Telegram settings:
    - [ ] `telegram_bot_token: str`
    - [ ] `telegram_bot_token_file: Optional[Path]`
    - [ ] `telegram_webhook_url: str`
    - [ ] `telegram_webhook_secret: str`
  - [ ] OpenAI settings:
    - [ ] `openai_api_key: str`
    - [ ] `openai_api_key_file: Optional[Path]`
    - [ ] `openai_model: str = "gpt-4o-2024-11-20"`
    - [ ] `openai_max_retries: int = 3`
    - [ ] `openai_timeout: int = 30`
  - [ ] Deepgram settings:
    - [ ] `deepgram_api_key: str`
    - [ ] `deepgram_api_key_file: Optional[Path]`
    - [ ] `deepgram_model: str = "nova-3"`
    - [ ] `deepgram_language: str = "en"`
  - [ ] App settings:
    - [ ] `app_env: str = "development"`
    - [ ] `app_debug: bool = False`
    - [ ] `app_port: int = 8443`
    - [ ] `metrics_port: int = 8000`
- [ ] Implement file reading for Docker secrets:
  - [ ] Create `read_secret_file` method
  - [ ] Add validators for `*_file` fields
- [ ] Add model_config with env prefix and case sensitivity
- [ ] Create settings instance singleton pattern
- [ ] Write tests for Settings class:
  - [ ] Test env var reading
  - [ ] Test file secret reading
  - [ ] Test validation errors
  - [ ] Test default values
- [ ] Run tests: `uv run pytest tests/core/test_settings.py -v`

### Day 4: Bot Setup & Webhook
- [ ] Create `src/main.py`
- [ ] Add async main function with proper logging setup
- [ ] Create `src/core/bot.py`:
  - [ ] Initialize Bot instance with settings
  - [ ] Initialize Dispatcher
  - [ ] Create webhook setup function
  - [ ] Create webhook removal function
- [ ] Add aiohttp dependency: `uv add aiohttp==3.11.13`
- [ ] Create `src/core/server.py`:
  - [ ] Create aiohttp.Application
  - [ ] Add webhook endpoint `/webhook/{token}`
  - [ ] Add health check endpoint `/health`
  - [ ] Add metrics placeholder endpoint `/metrics`
  - [ ] Implement proper error handling
- [ ] Create `src/core/middleware.py`:
  - [ ] Create logging middleware
  - [ ] Create error handling middleware
  - [ ] Create request ID middleware
- [ ] Update main.py:
  - [ ] Start web server on configured ports
  - [ ] Setup webhook on startup
  - [ ] Remove webhook on shutdown
  - [ ] Implement graceful shutdown
- [ ] Test webhook locally with ngrok:
  - [ ] Document ngrok setup in README
  - [ ] Test webhook registration
  - [ ] Test health endpoint

### Day 5: Basic Commands
- [ ] Create `src/handlers/commands.py`
- [ ] Create command router using aiogram.Router
- [ ] Implement `/start` command:
  - [ ] Create welcome message
  - [ ] Add inline keyboard with "Authorize" button
  - [ ] Handle user first interaction
- [ ] Implement `/help` command:
  - [ ] Create help text with examples
  - [ ] Format with Markdown
  - [ ] Include all available commands
- [ ] Create `src/handlers/__init__.py`:
  - [ ] Import all routers
  - [ ] Create register_handlers function
- [ ] Register handlers in main dispatcher
- [ ] Write tests for commands:
  - [ ] Mock telegram types
  - [ ] Test command responses
  - [ ] Test keyboard generation
- [ ] Test bot with BotFather token

## Week 2: AI Integration & Docker

### Day 6-7: OpenAI & Instructor Setup
- [ ] Add OpenAI dependencies:
  - [ ] `uv add openai==1.59.4`
  - [ ] `uv add instructor==1.7.2`
- [ ] Create `src/services/openai_service.py`:
  - [ ] Initialize OpenAI client with settings
  - [ ] Apply instructor patch
  - [ ] Create parse_task method
  - [ ] Implement retry logic with exponential backoff
  - [ ] Add timeout handling
- [ ] Create `src/models/task.py`:
  - [ ] Define TaskSchema with Pydantic:
    - [ ] `content: str` with validation
    - [ ] `description: Optional[str]`
    - [ ] `due_string: Optional[str]`
    - [ ] `priority: Optional[int]` with Field(ge=1, le=4)
    - [ ] `project_name: Optional[str]`
    - [ ] `labels: Optional[List[str]]`
    - [ ] `recurrence: Optional[str]`
    - [ ] `duration: Optional[int]` (in minutes)
  - [ ] Add field validators
  - [ ] Add model examples
- [ ] Create `src/core/exceptions.py`:
  - [ ] Define base BotError
  - [ ] Define OpenAIError
  - [ ] Define ValidationError
  - [ ] Define RateLimitError
- [ ] Implement profanity filter:
  - [ ] Add better-profanity: `uv add better-profanity==0.7.0`
  - [ ] Create filter function
  - [ ] Apply before OpenAI calls
- [ ] Write comprehensive tests:
  - [ ] Mock OpenAI responses
  - [ ] Test retry logic
  - [ ] Test profanity filter
  - [ ] Test schema validation

### Day 8: Text Message Handler
- [ ] Create `src/handlers/messages.py`
- [ ] Create message router
- [ ] Implement text message handler:
  - [ ] Filter for text messages only
  - [ ] Call OpenAI service
  - [ ] Handle parsing errors
  - [ ] Send formatted response
- [ ] Create `src/utils/formatters.py`:
  - [ ] Create task_to_telegram_html function
  - [ ] Handle None values properly
  - [ ] Format dates nicely
  - [ ] Add emoji indicators
- [ ] Implement typing action:
  - [ ] Show "typing..." while processing
  - [ ] Handle long operations
- [ ] Add rate limiting per user:
  - [ ] Track message counts in memory
  - [ ] Return rate limit errors
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
- [ ] Add Deepgram SDK: `uv add deepgram-sdk==3.10.1`
- [ ] Create `src/services/deepgram_service.py`:
  - [ ] Initialize Deepgram client
  - [ ] Create transcribe_audio method
  - [ ] Handle different audio formats
  - [ ] Add language detection
  - [ ] Implement timeout handling
- [ ] Create `src/services/transcription.py`:
  - [ ] Define abstract transcriber
  - [ ] Implement Deepgram transcriber
  - [ ] Add error handling
- [ ] Update voice processor:
  - [ ] Download telegram file
  - [ ] Convert if needed (ffmpeg)
  - [ ] Call transcription service
  - [ ] Handle errors gracefully
- [ ] Add ffmpeg to Docker image
- [ ] Test with various audio formats:
  - [ ] Voice notes (OGG)
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
- [ ] Add httpx: `uv add httpx==0.28.1`
- [ ] Create `src/services/todoist_service.py`:
  - [ ] Create async HTTP client
  - [ ] Implement OAuth methods
  - [ ] Implement create_task method
  - [ ] Add get_projects method
  - [ ] Add get_labels method
- [ ] Create `src/core/rate_limiter.py`:
  - [ ] Implement token bucket algorithm
  - [ ] 450 requests per 15 minutes
  - [ ] Per-user tracking
  - [ ] Add Redis backend later
- [ ] Add Todoist exceptions:
  - [ ] TodoistError
  - [ ] QuotaExceededError
  - [ ] InvalidTokenError
- [ ] Test with mock Todoist API:
  - [ ] Create mock responses
  - [ ] Test rate limiting
  - [ ] Test error handling

## Week 4: OAuth & Database

### Day 16-17: Database Setup
- [ ] Add database dependencies:
  - [ ] `uv add asyncpg==0.30.0`
  - [ ] `uv add sqlalchemy==2.0.37`
  - [ ] `uv add alembic==1.14.0`
- [ ] Create `src/models/database.py`:
  - [ ] Define User model:
    - [ ] id: UUID primary key
    - [ ] telegram_user_id: BigInt unique
    - [ ] telegram_username: String optional
    - [ ] todoist_api_token: Text (encrypted)
    - [ ] default_project: String optional
    - [ ] language: String default='en'
    - [ ] created_at: DateTime
    - [ ] updated_at: DateTime
    - [ ] is_active: Boolean
    - [ ] task_count: Integer default=0
  - [ ] Create database session manager
  - [ ] Add connection pool config
- [ ] Create `src/core/encryption.py`:
  - [ ] Use cryptography library
  - [ ] Implement encrypt_token method
  - [ ] Implement decrypt_token method
  - [ ] Use Fernet symmetric encryption
- [ ] Set up Alembic:
  - [ ] Initialize alembic
  - [ ] Create first migration
  - [ ] Add migration to startup
- [ ] Create `src/repositories/user_repo.py`:
  - [ ] Create get_user_by_telegram_id
  - [ ] Create create_or_update_user
  - [ ] Create delete_user
  - [ ] Add transaction handling

### Day 18: Personal API Token Setup
- [ ] Create `/setup` command handler:
  - [ ] Send instructions with link to Todoist API token page
  - [ ] Include step-by-step guide with screenshots
  - [ ] Wait for user to send token
- [ ] Create token validation:
  - [ ] Test token with Todoist API
  - [ ] Check if token is valid
  - [ ] Return user info and available projects
- [ ] Update /start command:
  - [ ] Check if user has token in DB
  - [ ] If not, redirect to /setup
  - [ ] If yes, show main menu
- [ ] Create `src/middleware/auth.py`:
  - [ ] Check user in database
  - [ ] Decrypt token if exists
  - [ ] Add to context
  - [ ] Handle unauthorized users
- [ ] Add token management commands:
  - [ ] `/setup` - add/update token
  - [ ] `/revoke` - remove token
  - [ ] `/test` - test current token
- [ ] Test token flow:
  - [ ] Test token validation
  - [ ] Test token storage
  - [ ] Test middleware

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