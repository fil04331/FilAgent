# User Feedback & Analytics System

## Overview

The feedback system allows users to rate their interactions with FilAgent, capturing valuable data to improve the model over time. Feedback is stored asynchronously to avoid impacting response times.

## Architecture

- **Database**: SQLite (`memory/analytics.sqlite`)
- **API Endpoint**: `POST /api/v1/feedback/{conversation_id}`
- **Storage**: Async background tasks (FastAPI BackgroundTasks)
- **Hashing**: SHA256 for input/output tracking

## Database Schema

### `interaction_logs` Table

| Column                  | Type      | Description                                    |
|------------------------|-----------|------------------------------------------------|
| `id`                   | INTEGER   | Primary key (auto-increment)                   |
| `conversation_id`      | TEXT      | References the conversation                    |
| `input_hash`           | TEXT      | SHA256 hash of user input                      |
| `output_hash`          | TEXT      | SHA256 hash of assistant response              |
| `user_feedback_score`  | INTEGER   | Rating from 1 (poor) to 5 (excellent)          |
| `user_feedback_text`   | TEXT      | Optional textual feedback                      |
| `latency_ms`           | REAL      | Response latency in milliseconds               |
| `tokens_used`          | INTEGER   | Total tokens (prompt + completion)             |
| `created_at`           | TIMESTAMP | Timestamp of feedback submission               |
| `metadata`             | TEXT      | JSON metadata (submitted_at, message_count)    |

### Indexes

- `idx_conversation_id`: Fast lookup by conversation
- `idx_feedback_score`: Fast filtering by rating
- `idx_created_at`: Fast time-based queries

## API Usage

### Submit Feedback

**Endpoint**: `POST /api/v1/feedback/{conversation_id}`

**Request Body**:
```json
{
  "score": 5,
  "text": "Excellent response!",
  "latency_ms": 125.5,
  "tokens_used": 245
}
```

**Fields**:
- `score` (required): Integer 1-5
- `text` (optional): String, max 2000 characters
- `latency_ms` (optional): Float >= 0
- `tokens_used` (optional): Integer >= 0

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Feedback received and will be processed",
  "conversation_id": "conv-123",
  "feedback_score": 5
}
```

**Error Responses**:
- `404`: Conversation not found
- `422`: Validation error (invalid score, text too long, etc.)

### Example Usage

```bash
# 1. Have a conversation
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Explain quantum computing"}],
    "conversation_id": "demo-123"
  }'

# 2. Submit feedback
curl -X POST http://localhost:8000/api/v1/feedback/demo-123 \
  -H "Content-Type: application/json" \
  -d '{
    "score": 5,
    "text": "Clear and concise explanation",
    "latency_ms": 150.0,
    "tokens_used": 300
  }'
```

## Python API

### Store Feedback Programmatically

```python
from memory.analytics import add_interaction_log

add_interaction_log(
    conversation_id="conv-123",
    user_feedback_score=5,
    user_feedback_text="Great answer!",
    input_hash="abc123...",
    output_hash="def456...",
    latency_ms=125.5,
    tokens_used=245,
    metadata={"source": "web_ui"}
)
```

### Retrieve Feedback

```python
from memory.analytics import get_interaction_logs, get_feedback_stats

# Get all feedback for a conversation
logs = get_interaction_logs(conversation_id="conv-123")

# Filter by score range
high_rated = get_interaction_logs(min_score=4, limit=100)
low_rated = get_interaction_logs(max_score=2)

# Get aggregated statistics
stats = get_feedback_stats()
print(f"Average score: {stats['avg_score']:.2f}/5")
print(f"Total feedback: {stats['total_count']}")
print(f"5-star ratings: {stats['score_5']}")
```

## Hash Computation

Input and output hashes enable linking feedback to specific request/response pairs:

```python
from memory.analytics import compute_hash

input_hash = compute_hash("User's question")
output_hash = compute_hash("Agent's response")
```

Hashes are SHA256 (64 hex characters).

## Async Background Processing

Feedback storage happens in a background task to avoid blocking the API response:

```python
from fastapi import BackgroundTasks

def store_feedback():
    # Long-running database operation
    add_interaction_log(...)

background_tasks.add_task(store_feedback)
```

This ensures users receive an immediate response while the feedback is being persisted.

## Analytics Queries

### Get Feedback Distribution

```python
stats = get_feedback_stats()
distribution = {
    "5 stars": stats['score_5'],
    "4 stars": stats['score_4'],
    "3 stars": stats['score_3'],
    "2 stars": stats['score_2'],
    "1 star": stats['score_1']
}
```

### Average Performance Metrics

```python
stats = get_feedback_stats()
avg_latency = stats['avg_latency_ms']
avg_tokens = stats['avg_tokens']
```

### Conversation-Specific Stats

```python
stats = get_feedback_stats(conversation_id="conv-123")
```

## Testing

### Run Tests

```bash
# Analytics module tests
pytest tests/test_analytics.py -v

# Feedback API tests
pytest tests/test_feedback_api.py -v
```

### Test Fixtures

Tests use isolated temporary databases:

```python
def test_feedback(temp_analytics_db):
    # temp_analytics_db provides isolated SQLite database
    # Automatically cleaned up after test
    ...
```

## Data Retention

Feedback data retention is not currently enforced. To implement retention:

```python
from memory.analytics import get_connection
from datetime import datetime, timedelta

def cleanup_old_feedback(days=90):
    conn = get_connection()
    cutoff = datetime.now() - timedelta(days=days)
    conn.execute("DELETE FROM interaction_logs WHERE created_at < ?", (cutoff,))
    conn.commit()
```

## Future Enhancements

Potential improvements to the feedback system:

1. **Sentiment Analysis**: Analyze `user_feedback_text` with NLP
2. **Trend Detection**: Identify patterns in feedback over time
3. **Model Improvement**: Use feedback to fine-tune the LLM
4. **Dashboard**: Visualize feedback metrics with Grafana/Tableau
5. **Export**: Export feedback data for external analysis
6. **Webhooks**: Notify on low ratings for immediate attention

## Security Considerations

- **PII Detection**: Feedback text should be scanned for PII before storage
- **Rate Limiting**: Implement rate limits on feedback endpoint to prevent abuse
- **Authentication**: Add authentication when feedback includes user identity
- **Data Privacy**: Comply with GDPR/Law 25 for data retention and deletion

## Troubleshooting

### "Conversation not found" Error

Ensure the conversation exists in `memory/episodic.sqlite`:

```python
from memory.episodic import get_messages
messages = get_messages("conv-123")
```

### Database Locked Error

SQLite may lock if accessed concurrently. Consider:
- Using WAL mode: `PRAGMA journal_mode=WAL`
- Connection pooling
- Migrating to PostgreSQL for high concurrency

### Background Task Not Executing

Check server logs for exceptions in the background task. Common issues:
- Database connection errors
- Import errors
- Permission issues

## References

- Source code: `memory/analytics.py`
- API endpoint: `runtime/server.py` (lines 343-434)
- Tests: `tests/test_analytics.py`, `tests/test_feedback_api.py`
- Fixtures: `tests/conftest.py` (temp_analytics_db fixture)
