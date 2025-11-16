# Perplexity API Integration

**Version**: 1.0.0
**Last Updated**: 2025-11-16
**Status**: Production Ready

FilAgent now supports **Perplexity API** as an alternative to local llama.cpp models, enabling cloud-based LLM inference with real-time web search capabilities.

## Table of Contents

1. [Why Perplexity?](#-why-perplexity)
2. [Installation](#-installation)
3. [Quick Start](#-quick-start)
4. [Available Models](#-available-models)
5. [Configuration](#-configuration)
6. [Examples](#-examples)
7. [Testing](#-testing)
8. [Pricing Considerations](#-pricing-considerations)
9. [Security Best Practices](#-security-best-practices)
10. [Troubleshooting](#-troubleshooting)
11. [Comparison: Perplexity vs llama.cpp](#-comparison-perplexity-vs-llamacpp)
12. [Resources](#-resources)
13. [Next Steps](#-next-steps)

---

## 🎯 Why Perplexity?

- **Zero Infrastructure**: No need to download or manage local models
- **Real-Time Search**: Sonar models include up-to-date web search results
- **High Performance**: Access to latest Llama 3.1 models optimized for speed
- **Cost Effective**: Pay-per-use pricing with competitive rates
- **Easy Setup**: Just add an API key and start using

---

## 📦 Installation

### Prerequisites

- Python 3.10 or higher
- FilAgent installed
- Internet connection (for API access)
- Perplexity API key (free tier available)

### 1. Install Dependencies

FilAgent uses PDM for dependency management. The `openai` package is required for Perplexity integration.

```bash
# Install FilAgent with ML dependencies (includes openai package)
pdm install --with ml

# Or install just the openai package
pdm add openai

# Legacy pip installation (not recommended)
pip install openai
```

**Note**: The `ml` dependency group includes additional packages for machine learning features (FAISS, sentence-transformers, etc.). If you only need Perplexity API support, you can install just `openai`.

### 2. Get API Key

1. Sign up at [Perplexity AI](https://www.perplexity.ai)
2. Navigate to [API Settings](https://www.perplexity.ai/settings/api)
3. Generate a new API key (format: `pplx-...`)

### 3. Configure Environment

```bash
# Method 1: Environment variable
export PERPLEXITY_API_KEY="pplx-your-api-key-here"

# Method 2: .env file
cp .env.example .env
# Edit .env and add:
# PERPLEXITY_API_KEY=pplx-your-api-key-here
```

---

## 🚀 Quick Start

### Basic Usage

```python
from runtime.model_interface import init_model, GenerationConfig

# Initialize Perplexity client
# The model_path parameter specifies which Perplexity model to use
model = init_model(
    backend="perplexity",
    model_path="llama-3.1-sonar-large-128k-online",
    config={}  # Uses PERPLEXITY_API_KEY from environment
)

# Generate text with configuration
config = GenerationConfig(
    temperature=0.2,    # Lower = more deterministic
    max_tokens=512,     # Maximum response length
    top_p=0.95
)

result = model.generate(
    prompt="What are the latest AI developments in 2025?",
    config=config,
    system_prompt="You are a knowledgeable AI researcher."
)

# Display results
print(result.text)
print(f"Tokens used: {result.total_tokens}")
print(f"Finish reason: {result.finish_reason}")
```

### Using Configuration File

```bash
# Use the Perplexity configuration
# (Edit config/agent.perplexity.yaml if needed)
export PERPLEXITY_API_KEY="pplx-your-key"
python runtime/server.py --config config/agent.perplexity.yaml
```

---

## 🤖 Available Models

### Sonar Models (with Web Search)

| Model | Description | Best For |
|-------|-------------|----------|
| `llama-3.1-sonar-small-128k-online` | Fast, cost-effective | Quick queries, high volume |
| `llama-3.1-sonar-large-128k-online` | Balanced performance | General use, best value |
| `llama-3.1-sonar-huge-128k-online` | Best quality | Complex questions, research |

**Features**: Real-time web search, up-to-date information, citation support

### Chat Models (no Search)

| Model | Description | Best For |
|-------|-------------|----------|
| `llama-3.1-8b-instruct` | Fast, lightweight | Code generation, structured tasks |
| `llama-3.1-70b-instruct` | High quality | Complex reasoning, long context |

**Features**: No web search, pure LLM inference, faster response time

---

## ⚙️ Configuration

### GenerationConfig Parameters

```python
from runtime.model_interface import GenerationConfig

config = GenerationConfig(
    temperature=0.2,      # Lower = more deterministic (0.0-1.0)
    top_p=0.95,           # Nucleus sampling (0.0-1.0)
    max_tokens=1024,      # Maximum tokens to generate
    seed=42               # For reproducibility (Perplexity ignores this)
)
```

### Environment Variables

```bash
# Required
PERPLEXITY_API_KEY=pplx-your-api-key-here

# Optional
PERPLEXITY_MODEL=llama-3.1-sonar-large-128k-online  # Default model
```

---

## 📖 Examples

### Example 1: Real-Time Research

```python
# Run the example
export PERPLEXITY_API_KEY="pplx-your-key"
python examples/perplexity_example.py
```

### Example 2: Code Generation

```python
from runtime.model_interface import init_model, GenerationConfig

model = init_model(
    backend="perplexity",
    model_path="llama-3.1-8b-instruct",  # Fast model for code
    config={}
)

result = model.generate(
    prompt="Write a Python function to calculate Fibonacci numbers with memoization",
    config=GenerationConfig(temperature=0.1, max_tokens=256),
    system_prompt="You are an expert Python developer."
)

print(result.text)
```

### Example 3: HTN Planning with Perplexity

```python
from runtime.agent import Agent
from runtime.config import get_config

# Load Perplexity configuration
# This configuration uses Perplexity instead of llama.cpp
config = get_config("config/agent.perplexity.yaml")

# Initialize agent with Perplexity backend
agent = Agent(config=config)
agent.initialize_model()

# Use HTN planning with real-time web search
# HTN (Hierarchical Task Network) will decompose complex queries
response = agent.run("Research and summarize the latest Python 3.13 features")

print(response["final_answer"])

# Access decision records for compliance
if response.get("decision_record"):
    print(f"Decision Record ID: {response['decision_record']['dr_id']}")
```

---

## 🧪 Testing

### Unit Tests

```bash
# Run Perplexity tests (uses mocks, no API key needed)
pdm run pytest tests/test_perplexity_interface.py -v
```

### Integration Tests

```bash
# Run with real API (requires API key)
export PERPLEXITY_API_KEY="pplx-your-key"
pdm install --with ml
pdm run pytest tests/test_perplexity_interface.py -v -m integration
```

---

## 💰 Pricing Considerations

Perplexity charges per token used. Key tips:

1. **Choose the Right Model**:
   - Use `sonar-small` for high-volume, simple queries
   - Use `sonar-large` for balanced performance
   - Use chat models when you don't need web search

2. **Optimize Token Usage**:
   - Set appropriate `max_tokens` limits
   - Use concise system prompts
   - Cache frequently used results

3. **Monitor Usage**:
   ```python
   result = model.generate(...)
   print(f"Tokens: {result.total_tokens}")  # Track token usage
   ```

---

## 🔐 Security Best Practices

### 1. API Key Management

**Never commit API keys**:
```bash
# Add to .gitignore
echo ".env" >> .gitignore
echo "*.env" >> .gitignore
```

**Use environment variables exclusively**:
```python
# ✅ SECURE - Using environment variable
api_key = os.getenv("PERPLEXITY_API_KEY")

# ❌ INSECURE - Hardcoded key (NEVER do this)
api_key = "pplx-12345..."
```

**Never log API keys**:
```python
# ✅ SECURE - Redacted logging
print("✓ Found API key: [REDACTED]")

# ❌ INSECURE - Partial key exposure (even truncated keys are sensitive)
print(f"API key: {api_key[:10]}...")
```

### 2. Rate Limiting Protection

FilAgent implements automatic rate limiting to prevent API abuse:

**Built-in Rate Limiter**:
- **Default limits**: 10 requests/minute, 500 requests/hour
- **Exponential backoff**: Automatic retry with increasing delays
- **Thread-safe**: Safe for concurrent usage
- **Cost protection**: Prevents unexpected API charges

**Configuration**:
```python
# Rate limiter is automatically configured in PerplexityInterface
# Located at: runtime/utils/rate_limiter.py

# Customize limits if needed
rate_limiter = get_rate_limiter(
    requests_per_minute=10,   # Conservative default
    requests_per_hour=500      # Adjust based on your quota
)
```

**Benefits**:
- Prevents rate limit errors (429 status codes)
- Automatic retry with exponential backoff
- Protects against API cost overruns
- Compliant with Perplexity's usage policies

### 3. Error Message Sanitization

All error messages are automatically sanitized to prevent information leakage:

**Protected Information**:
- API keys and tokens are never exposed in errors
- Connection strings are sanitized
- Stack traces are filtered for sensitive data
- Generic error messages for authentication failures

**Example**:
```python
# Internal error handling (automatic)
if "api_key" in error_message.lower():
    safe_error = "Authentication error. Please check your API credentials."
```

### 4. Secure Configuration

**Environment Setup**:
```bash
# Create secure .env file
touch .env
chmod 600 .env  # Restrict to owner only

# Add API key
echo 'PERPLEXITY_API_KEY="pplx-your-key-here"' >> .env
```

**Docker Secrets** (if using containers):
```yaml
# docker-compose.yml
services:
  filagent:
    secrets:
      - perplexity_api_key
    environment:
      PERPLEXITY_API_KEY_FILE: /run/secrets/perplexity_api_key

secrets:
  perplexity_api_key:
    external: true
```

### 5. Key Rotation Strategy

**Rotation Schedule**:
- **Monthly**: Rotate production keys
- **Quarterly**: Rotate development keys
- **Immediately**: After any suspected compromise

**Rotation Process**:
1. Generate new key in Perplexity dashboard
2. Update environment variable
3. Test with new key
4. Revoke old key after confirming new key works

### 6. Monitoring & Auditing

**Usage Monitoring**:
```python
# Track token usage for cost control
result = model.generate(...)
print(f"Tokens used: {result.total_tokens}")

# Log to monitoring system
logger.info(f"API call: {result.total_tokens} tokens")
```

**Security Auditing**:
- All API calls are logged (without sensitive data)
- Decision Records track API usage
- Rate limiter logs rejected requests
- Failed authentication attempts are tracked

### 7. Compliance Requirements

**Loi 25 / PIPEDA Compliance**:
- ✅ No PII in logs (automatic redaction)
- ✅ Secure credential storage (environment variables)
- ✅ Audit trail for all API calls
- ✅ Rate limiting prevents abuse

**Security Certifications**:
- Follow NIST guidelines for API key management
- Implement defense-in-depth strategy
- Regular security assessments

### 8. Incident Response

**If API Key is Compromised**:
1. **Immediately**: Revoke key in Perplexity dashboard
2. **Generate**: Create new API key
3. **Update**: Change all environment variables
4. **Audit**: Review logs for unauthorized usage
5. **Report**: Document incident in Decision Record

### 9. Development Best Practices

**Local Development**:
```bash
# Use separate keys for dev/prod
export PERPLEXITY_API_KEY_DEV="pplx-dev-key"
export PERPLEXITY_API_KEY_PROD="pplx-prod-key"
```

**CI/CD Pipeline**:
- Use secrets management (GitHub Secrets, GitLab CI Variables)
- Never echo or print keys in CI logs
- Rotate CI/CD keys quarterly

### 10. Security Checklist

Before deploying to production:

- [ ] API key stored in environment variable only
- [ ] No keys in source code or configuration files
- [ ] Rate limiting enabled and configured
- [ ] Error messages sanitized
- [ ] Logging excludes sensitive data
- [ ] Key rotation schedule established
- [ ] Monitoring and alerting configured
- [ ] Incident response plan documented
- [ ] .env file excluded from version control
- [ ] Proper file permissions on .env (600)

---

## 🐛 Troubleshooting

### "openai package not installed"

```bash
# Solution
pdm install --with ml
```

### "PERPLEXITY_API_KEY not found"

```bash
# Solution 1: Set environment variable
export PERPLEXITY_API_KEY="pplx-your-key"

# Solution 2: Pass in config
model = init_model(
    backend="perplexity",
    model_path="llama-3.1-sonar-large-128k-online",
    config={"api_key": "pplx-your-key"}
)
```

### "API Error" / Rate Limiting

```python
# Implement exponential backoff
import time

for attempt in range(3):
    try:
        result = model.generate(prompt, config)
        break
    except Exception as e:
        if attempt < 2:
            wait_time = 2 ** attempt
            print(f"Retrying in {wait_time}s...")
            time.sleep(wait_time)
        else:
            raise
```

---

## 📊 Comparison: Perplexity vs llama.cpp

| Feature | Perplexity API | llama.cpp (Local) |
|---------|---------------|-------------------|
| **Setup** | ✅ Instant (API key only) | ⚠️ Complex (download models) |
| **Cost** | 💰 Pay-per-use | ✅ Free (after hardware) |
| **Speed** | ✅ Fast (cloud infrastructure) | ⚠️ Depends on hardware |
| **Privacy** | ⚠️ Data sent to cloud | ✅ 100% local |
| **Web Search** | ✅ Sonar models | ❌ Not available |
| **Offline** | ❌ Requires internet | ✅ Works offline |
| **Scalability** | ✅ Infinite (cloud) | ⚠️ Limited by hardware |

**Choose Perplexity when**:
- You need real-time web search
- You want zero infrastructure management
- You need high scalability

**Choose llama.cpp when**:
- Privacy is critical (on-premise)
- You want to avoid API costs
- You need offline operation

---

## 🔗 Resources

- [Perplexity API Documentation](https://docs.perplexity.ai)
- [Perplexity Pricing](https://www.perplexity.ai/pricing)
- [Model Comparison](https://docs.perplexity.ai/docs/model-cards)
- [FilAgent Example](/examples/perplexity_example.py)
- [Configuration Reference](/config/agent.perplexity.yaml)
- [Model Interface Implementation](/runtime/model_interface.py)

---

## ✅ Next Steps

1. **Get API Key**: https://www.perplexity.ai/settings/api
2. **Install Dependencies**: `pdm install --with ml`
3. **Run Example**: `python examples/perplexity_example.py`
4. **Read Configuration**: `config/agent.perplexity.yaml`
5. **Explore Models**: Try different Perplexity models for your use case

---

---

## 📚 Related Documentation

- [Main README](/README.md) - Project overview and setup
- [CLAUDE.md](/CLAUDE.md) - Comprehensive guide for AI assistants
- [Configuration Guide](/docs/CONFIGURATION_CAPACITES.md) - Detailed configuration options
- [Dependency Management](/docs/DEPENDENCY_MANAGEMENT.md) - PDM and dependency setup
- [Benchmarks](/docs/BENCHMARKS.md) - Performance evaluation

---

## 💬 Support

**Questions or Issues?**
- GitHub Issues: https://github.com/fil04331/FilAgent/issues
- Documentation: [README.md](/README.md)
- Security Contact: security@filagent.ai
- General Support: Via GitHub issues
