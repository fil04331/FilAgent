# Perplexity API Integration

FilAgent now supports **Perplexity API** as an alternative to local llama.cpp models, enabling cloud-based LLM inference with real-time web search capabilities.

---

## 🎯 Why Perplexity?

- **Zero Infrastructure**: No need to download or manage local models
- **Real-Time Search**: Sonar models include up-to-date web search results
- **High Performance**: Access to latest Llama 3.1 models optimized for speed
- **Cost Effective**: Pay-per-use pricing with competitive rates
- **Easy Setup**: Just add an API key and start using

---

## 📦 Installation

### 1. Install Dependencies

```bash
# Install FilAgent with ML dependencies (includes openai package)
pdm install --with ml

# Or with pip
pip install openai
```

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
model = init_model(
    backend="perplexity",
    model_path="llama-3.1-sonar-large-128k-online",
    config={}  # Uses PERPLEXITY_API_KEY from environment
)

# Generate text
config = GenerationConfig(temperature=0.2, max_tokens=512)
result = model.generate(
    prompt="What are the latest AI developments in 2025?",
    config=config,
    system_prompt="You are a knowledgeable AI researcher."
)

print(result.text)
print(f"Tokens used: {result.total_tokens}")
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
config = get_config("config/agent.perplexity.yaml")

# Initialize agent with Perplexity
agent = Agent(config=config)

# Use HTN planning with real-time web search
response = agent.run("Research and summarize the latest Python 3.13 features")

print(response["final_answer"])
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

1. **Never commit API keys**:
   ```bash
   # Add to .gitignore
   echo ".env" >> .gitignore
   ```

2. **Use environment variables**:
   ```python
   # ✅ Good
   api_key = os.getenv("PERPLEXITY_API_KEY")

   # ❌ Bad - hardcoded key
   api_key = "pplx-12345..."
   ```

3. **Rotate keys regularly**:
   - Generate new keys monthly
   - Revoke old keys in Perplexity dashboard

4. **Monitor usage**:
   - Check usage in Perplexity dashboard
   - Set up billing alerts

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
- [FilAgent Example](../examples/perplexity_example.py)
- [Configuration Reference](../config/agent.perplexity.yaml)

---

## ✅ Next Steps

1. **Get API Key**: https://www.perplexity.ai/settings/api
2. **Install Dependencies**: `pdm install --with ml`
3. **Run Example**: `python examples/perplexity_example.py`
4. **Read Configuration**: `config/agent.perplexity.yaml`
5. **Explore Models**: Try different Perplexity models for your use case

---

**Questions or Issues?**
- GitHub Issues: https://github.com/fil04331/FilAgent/issues
- Documentation: [README.md](../README.md)
