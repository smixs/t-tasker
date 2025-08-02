# TaskerBot Stress Testing

Comprehensive stress testing framework for TaskerBot with realistic load patterns and detailed metrics.

## Architecture

The stress testing framework consists of several modules:

- **telegram_simulator.py**: Creates proper aiogram 3 Update objects (frozen Pydantic models)
- **load_generator.py**: Generates realistic user behavior patterns
- **mock_services.py**: Realistic mocks for external services (OpenAI, Deepgram, Todoist)
- **metrics_collector.py**: Comprehensive metrics collection (latency, errors, throughput)
- **test_real_stress.py**: Main test scenarios implementation

## Features

### Realistic Traffic Mix
- 30% text messages with tasks
- 20% voice messages (1-15 seconds)
- 20% commands (/start, /help, /recent, etc.)
- 15% message edits
- 15% callback button presses

### Realistic Service Behavior
- **OpenAI**: 100-300ms delays, rate limiting, 2% failure rate
- **Deepgram**: 200-500ms delays based on audio duration
- **Todoist**: 50-150ms delays, 450 req/15min rate limit
- **Bot API**: Tracked metrics for all method calls

### Comprehensive Metrics
- Latency: P50, P90, P95, P99, P99.9
- Throughput: Average, current, and peak RPS
- Errors: By type with samples
- Resources: CPU, memory, Redis connections
- Concurrency: Max concurrent requests

## Test Scenarios

### 1. Baseline Test
- 50 concurrent users
- 1 message/second per user
- 5 minutes duration
- Tests normal operating conditions

### 2. Peak Load Test
- 100 concurrent users
- Burst of 500 messages in 10 seconds
- Tests system behavior under sudden load spikes

### 3. Sustained Load Test
- 50 concurrent users
- 30 minutes continuous load
- Tests system stability and resource leaks

## Running Tests

### Run all tests:
```bash
uv run python run_stress_test.py
```

### Run specific test:
```bash
uv run python run_stress_test.py baseline
uv run python run_stress_test.py peak
uv run python run_stress_test.py sustained
```

### Quick verification:
```bash
uv run python tests/stress/test_quick_verify.py
```

### Run with pytest:
```bash
pytest tests/stress/test_real_stress.py -v -s -m stress
```

### Run specific scenario with pytest:
```bash
pytest tests/stress/test_real_stress.py::test_baseline_scenario -v -s
```

## Prerequisites

1. Redis must be running
2. PostgreSQL must be running
3. Test database should be configured
4. Dependencies installed: `uv sync`

## Understanding Results

### Success Criteria
- Success rate > 90%
- P95 latency < 4 seconds
- No memory leaks (stable memory usage)
- No Redis connection exhaustion

### Example Output
```
STRESS TEST METRICS SUMMARY
================================================================================

Test Duration: 300.45 seconds
Total Requests: 15,234
Success Rate: 98.76%

Throughput:
  Average: 50.71 req/s
  Current: 48.23 req/s
  Peak: 125.00 req/s

Latency (Overall):
  P50: 234.56ms
  P90: 567.89ms
  P95: 890.12ms
  P99: 1234.56ms
  P99.9: 2345.67ms
  Mean: 345.67ms (±234.56ms)

Errors:
  Total: 189
  Error Rate: 1.24%
  By Type:
    - RateLimitError: 123
    - OpenAIError: 45
    - TranscriptionError: 21

Resource Usage:
  CPU: avg=45.2%, max=78.9%
  Memory: avg=234.5MB, max=345.6MB
```

## Customization

### Modify Load Profile
Edit `LoadProfile` in test scenarios:
```python
custom_profile = LoadProfile(
    text_task_percent=0.40,      # More text tasks
    voice_message_percent=0.10,   # Fewer voice messages
    burst_probability=0.20,       # More bursts
    burst_size=10                 # Larger bursts
)
```

### Adjust Service Behavior
Modify mock service parameters:
```python
openai_mock = RealisticOpenAIMock(
    failure_rate=0.05,           # 5% failure rate
    rate_limit_threshold=50      # Lower rate limit
)
```

## Troubleshooting

### "Too many open files" error
Increase ulimit: `ulimit -n 4096`

### Redis connection errors
Check Redis is running and accessible

### High memory usage
Reduce concurrent users or test duration

### Database connection pool exhausted
Increase pool size in database settings