# PRD: TaskerBot - Telegram Bot for Todoist

**Version 4.0 / Simplified for Agencies**

## 1. Overview

**Vision**: Fast, voice-first task capture for busy agency teams. Text, voice, or video → Todoist task in <4 seconds.

**Goals**:
- Personal API tokens (no complex OAuth)
- Voice-first design for mobile use
- Quick commands for common tasks
- 99.8% uptime for reliability

**KPIs**:
- 90% of tasks created in ≤4 seconds
- Voice message success rate ≥95%
- Daily active users growth
- 60%+ tasks created via voice

## 2. Core Features

### 2.1 Message Processing Flow

Messages are processed through an async chain. Each processor returns: Handled, Skip, or Error.

| Step | Processor | Description |
|------|-----------|-------------|
| 1 | Commands | `/start`, `/setup`, `/help`, quick commands |
| 2 | Voice/Audio/Video | Transcription via Deepgram/Whisper |
| 3 | Text | Parse and create Todoist task |

### 2.2 Task Parsing (Instructor + GPT-4)

**Pydantic Schema**:
```python
from pydantic import BaseModel, Field

class TaskSchema(BaseModel):
    content: str
    description: str | None = None
    due_string: str | None = None  # "today", "tomorrow", "next Monday"
    priority: int | None = Field(ge=1, le=4)
    project_name: str | None = None
    labels: list[str] | None = None
    duration: int | None = None  # minutes
```

**AI Features**:
- Smart date parsing: "end of week" → "Friday"
- Client/project detection from context
- Priority inference from keywords ("urgent", "ASAP")
- Profanity filter (replace with *)

### 2.3 Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Welcome & check setup | Shows setup instructions |
| `/setup` | Configure Todoist token | Step-by-step guide |
| `/help` | Usage examples | Voice/text examples |
| `/t` | Quick task for today | `/t Call client about proposal` |
| `/tm` | Task for tomorrow | `/tm Review design drafts` |
| `/urgent` | High priority task | `/urgent Fix website bug` |
| `/meeting` | Meeting template | `/meeting ClientName 2pm` |
| `/stats` | Your task statistics | Daily/weekly summary |
| `/revoke` | Remove your token | Security feature |

## 3. Integrations

### 3.1 Speech Recognition

**Primary: Deepgram Nova-2**
- Cost: $0.0043/minute (cheaper than Whisper)
- Speed: 200-500ms latency
- Languages: English + Russian (auto-detect)
- Native OGG support (Telegram format)

**Fallback: faster-whisper**
- Local processing when Deepgram fails
- Model: base (good balance of speed/accuracy)
- Auto-download on first use

### 3.2 Todoist API

**Authentication**: Personal API tokens
- Users get token from todoist.com/prefs/integrations
- Encrypted storage in database
- No OAuth complexity

**Rate Limits**: 450 requests/15 min
- In-memory caching (5 min TTL)
- Projects, labels, user info cached
- Smart batching for efficiency

### 3.3 AI Processing

**OpenAI GPT-4**:
- Model: gpt-4o-2024-11-20
- Instructor for structured output
- 3 retries with exponential backoff
- Context includes common project names

## 4. Technical Requirements

### 4.1 Performance

| Metric | Target | Notes |
|--------|--------|-------|
| Latency P95 | <4 sec | From message to task created |
| Uptime | 99.8% | ~17 hours downtime/year |
| CPU Usage | ≤0.5 core | Efficient async processing |
| Memory | ≤512 MB | Lightweight design |
| Concurrent Users | 100+ | Async architecture |

### 4.2 Security & Privacy

- API tokens encrypted with Fernet
- No token sharing between users
- `/delete_my_data` for GDPR compliance
- Audit logs for all actions
- TLS 1.3 for all connections

### 4.3 Tech Stack

- **Language**: Python 3.12
- **Bot Framework**: aiogram 3.21+ (Router pattern)
- **Package Manager**: uv (NOT pip)
- **AI**: Instructor + OpenAI
- **Database**: PostgreSQL + asyncpg
- **Cache**: Redis (optional, in-memory fallback)
- **Deployment**: Docker on VPS

## 5. User Experience

### 5.1 Onboarding Flow

1. User sends `/start`
2. Bot checks if token exists
3. If not → `/setup` with visual guide
4. User gets token from Todoist
5. Sends token to bot
6. Bot validates & saves encrypted
7. Ready to use!

### 5.2 Voice-First Design

**Voice Note Flow**:
1. User records voice message
2. Bot shows "transcribing..." status
3. Transcription appears as preview
4. Task created with confirmation
5. Shows task details + Todoist link

**Smart Features**:
- Background noise handling
- Multiple language support
- Long message chunking (>5 min)
- Whisper fallback on errors

### 5.3 Quick Actions

**For Agencies**:
- Project shortcuts (last 5 used)
- Client name auto-complete
- Template messages for common tasks
- Bulk task creation (comma-separated)

## 6. Deployment

### 6.1 Docker Setup

**Multi-stage build**:
- Stage 1: Install dependencies with uv
- Stage 2: Slim runtime (<120MB)
- Non-root user (appuser)
- Health check endpoint

### 6.2 Infrastructure

**Minimal Requirements**:
- 1 vCPU, 1GB RAM VPS
- PostgreSQL (or SQLite for <50 users)
- Redis (optional)
- HTTPS domain for webhook

**Monitoring**:
- Health endpoint: `/health`
- Prometheus metrics: `/metrics`
- Error tracking: Sentry (optional)
- Logs: JSON format to stdout

## 7. Development Roadmap

### Phase 1: MVP (Week 1-2)
- [x] Basic bot structure
- [ ] Personal token auth via `/setup`
- [ ] Text → Todoist task
- [ ] Simple deployment

### Phase 2: Voice & Polish (Week 3-4)
- [ ] Deepgram integration
- [ ] Whisper fallback
- [ ] Quick commands (`/t`, `/tm`)
- [ ] Error handling

### Phase 3: Agency Features (Week 5-6)
- [ ] Project templates
- [ ] Team statistics
- [ ] Multi-language support
- [ ] Performance optimization

### Future Enhancements
- Slack/Discord integration
- Calendar sync for deadlines
- Voice responses
- Task templates library
- Team dashboards

## 8. Success Metrics

**Week 1**: 5+ daily active users
**Month 1**: 50+ tasks/day created
**Month 3**: 60%+ via voice
**Long-term**: Primary task tool for team

## 9. Simplified Architecture

```
User → Telegram → Bot (aiogram)
                    ↓
              Message Router
              ↙     ↓     ↘
        Commands  Voice  Text
              ↓     ↓     ↓
         Process  ASR   Parse
              ↓     ↓     ↓
              Task Schema
                   ↓
              Todoist API
                   ↓
              Confirmation → User
```

This simplified approach focuses on:
- Quick implementation
- Easy maintenance
- User-friendly setup
- Reliable performance
- Agency-specific features