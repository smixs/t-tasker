# TaskerBot Implementation Plan - Simplified Version

## Overview
Simplified 6-week plan focusing on Personal API tokens and quick implementation for agency teams.

## Week 1: Foundation & Basic Bot

### Day 1-2: Project Setup
1. **Environment Setup**
   - Install Python 3.12 and uv package manager
   - Create project structure with uv
   - Configure development tools (ruff, mypy, pytest)
   - Set up git repository

2. **Basic Dependencies**
   ```bash
   uv add aiogram==3.21.0
   uv add pydantic==2.10.4
   uv add pydantic-settings==2.7.0
   uv add python-dotenv==1.0.1
   uv add --dev ruff mypy pytest pytest-asyncio
   ```

### Day 3: Settings & Configuration
1. **Settings Class** (`src/core/settings.py`)
   - Environment variable reading
   - Support for Docker secrets (optional)
   - Validation with pydantic
   - Singleton pattern for settings

2. **Core Structure**
   ```
   src/
   ├── core/       # Settings, middleware, exceptions
   ├── handlers/   # Telegram command handlers
   ├── services/   # External API clients
   └── models/     # Pydantic schemas
   ```

### Day 4: Bot Infrastructure
1. **Main Bot Setup** (`src/main.py`)
   - Initialize aiogram Bot and Dispatcher
   - Simple webhook setup (polling for local dev)
   - Basic error handling
   - Graceful shutdown

2. **Health Check Server**
   - Simple aiohttp server on port 8000
   - `/health` endpoint returning OK
   - Ready for monitoring

### Day 5: Basic Commands
1. **Command Handlers** (`src/handlers/commands.py`)
   - `/start` - Check if user has token, show welcome
   - `/setup` - Guide to get Todoist token
   - `/help` - Usage examples
   - `/revoke` - Remove stored token

2. **Middleware** (`src/core/middleware.py`)
   - Logging middleware
   - Basic error handling
   - User context injection

## Week 2: Todoist Integration & AI

### Day 6-7: Personal Token Flow
1. **Token Management**
   - `/setup` command with visual guide
   - Token validation against Todoist API
   - Encrypted storage (Fernet)
   - Token status checking

2. **Database Models** (`src/models/database.py`)
   ```python
   class User:
       telegram_user_id: int
       telegram_username: str
       todoist_api_token: str  # encrypted
       default_project: str
       language: str = 'en'
       task_count: int = 0
   ```

### Day 8: Todoist Client
1. **API Client** (`src/services/todoist_service.py`)
   - Simple httpx-based client
   - Personal token authentication
   - Create task method
   - Get projects/labels (with caching)
   - Rate limiting (450/15min)

2. **In-Memory Cache**
   - Projects list (5 min TTL)
   - Labels list (5 min TTL)
   - User info cache

### Day 9: OpenAI Integration
1. **AI Service** (`src/services/openai_service.py`)
   - Instructor setup with GPT-4
   - Task parsing with retry logic
   - Profanity filter
   - Smart date/project detection

2. **Task Schema** (`src/models/task.py`)
   ```python
   class TaskSchema(BaseModel):
       content: str
       due_string: str | None
       priority: int | None = Field(ge=1, le=4)
       project_name: str | None
       labels: list[str] | None
   ```

### Day 10: Text Message Handler
1. **Message Processing**
   - Text message handler
   - Call OpenAI for parsing
   - Create task in Todoist
   - Send confirmation to user

2. **Quick Commands**
   - `/t` - Today task
   - `/tm` - Tomorrow task
   - `/urgent` - High priority

## Week 3: Voice & Advanced Features

### Day 11-12: Voice Processing
1. **Deepgram Integration** (`src/services/deepgram_service.py`)
   - Nova-2 model setup
   - OGG file handling (native)
   - Language detection
   - Error handling

2. **Voice Handler** (`src/handlers/voice.py`)
   - Download voice/video files
   - Send to Deepgram
   - Show "transcribing..." status
   - Process transcribed text

### Day 13: Whisper Fallback
1. **Local ASR** (`src/services/whisper_service.py`)
   - faster-whisper setup
   - Model caching
   - Fallback logic
   - Performance optimization

### Day 14: Chain of Responsibility
1. **Message Router** (`src/core/processors.py`)
   - Command processor
   - Voice processor
   - Text processor
   - Error handling chain

### Day 15: Error Handling
1. **Global Error Handler**
   - Custom exceptions
   - User-friendly messages
   - Fallback strategies
   - Error logging

## Week 4: Database & Security

### Day 16-17: PostgreSQL Setup
1. **Database Integration**
   - SQLAlchemy models
   - Asyncpg for async queries
   - Connection pooling
   - Migration setup (Alembic)

2. **User Repository** (`src/repositories/user_repo.py`)
   - CRUD operations
   - Token encryption/decryption
   - Transaction handling

### Day 18: Security Features
1. **Encryption** (`src/core/encryption.py`)
   - Fernet for token encryption
   - Key management
   - Secure token storage

2. **Auth Middleware**
   - Token validation
   - User context
   - Rate limiting per user

### Day 19: User Commands
1. **Additional Commands**
   - `/stats` - User statistics
   - `/settings` - Preferences
   - `/delete_my_data` - GDPR compliance

### Day 20: Testing
1. **Test Suite**
   - Unit tests for services
   - Integration tests
   - Mocked external APIs
   - 80%+ coverage target

## Week 5: Production Features

### Day 21-22: Docker & Deployment
1. **Docker Setup**
   - Multi-stage Dockerfile
   - Image size <120MB
   - docker-compose.yml
   - Health checks

2. **Environment Configuration**
   - Production .env setup
   - Secret management
   - Logging configuration

### Day 23: Monitoring
1. **Basic Monitoring**
   - Health endpoint
   - Simple metrics
   - Error tracking (optional Sentry)
   - Structured logging

### Day 24: Performance
1. **Optimization**
   - Connection pooling
   - Async everywhere
   - Caching strategy
   - Resource limits

### Day 25: Documentation
1. **User Documentation**
   - Setup guide
   - Command reference
   - FAQ section
   - Troubleshooting

## Week 6: Polish & Launch

### Day 26-27: Agency Features
1. **Templates & Shortcuts**
   - Meeting templates
   - Project shortcuts
   - Quick actions
   - Bulk operations

2. **Team Features**
   - Basic statistics
   - Usage reports
   - Project analytics

### Day 28: Load Testing
1. **Performance Testing**
   - Simulate 100+ users
   - Measure latencies
   - Find bottlenecks
   - Optimize queries

### Day 29: Final Testing
1. **End-to-End Testing**
   - Full user flows
   - Voice processing
   - Error scenarios
   - Recovery testing

### Day 30: Launch
1. **Production Deployment**
   - Deploy to VPS
   - DNS configuration
   - SSL setup
   - Monitoring active

## Key Simplifications

1. **No OAuth** - Personal API tokens only
2. **Simple Storage** - Start with SQLite option
3. **Minimal UI** - Text-based responses
4. **Basic Features First** - Add complexity later
5. **In-Memory Cache** - Redis optional

## Success Criteria

- Setup takes <2 minutes
- Voice tasks work 95%+ time
- <4 second response time
- Zero maintenance for weeks
- Clear error messages

## Future Enhancements

After launch, consider:
- Redis for caching
- OAuth support
- Slack integration
- Advanced analytics
- Team dashboards
- Calendar sync