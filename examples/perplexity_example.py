"""
Example: Using FilAgent with Perplexity API

This example demonstrates how to use Perplexity's API for LLM inference
instead of running a local model with llama.cpp.

Prerequisites:
1. Install ML dependencies: pdm install --with ml
2. Set PERPLEXITY_API_KEY environment variable
3. (Optional) Copy .env.example to .env and configure

Usage:
    export PERPLEXITY_API_KEY="pplx-your-api-key-here"
    python examples/perplexity_example.py
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from runtime.model_interface import (
    init_model,
    get_model,
    GenerationConfig,
)


def main():
    """Example usage of Perplexity API with FilAgent"""

    print("=" * 80)
    print("FilAgent - Perplexity API Example")
    print("=" * 80)

    # Check for API key
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        print("❌ PERPLEXITY_API_KEY not found in environment")
        print("\nPlease set it:")
        print('  export PERPLEXITY_API_KEY="pplx-your-api-key-here"')
        print("\nGet your API key from: https://www.perplexity.ai/settings/api")
        sys.exit(1)

    print("✓ Found API key: [REDACTED]")

    # Initialize Perplexity model
    print("\n" + "=" * 80)
    print("Initializing Perplexity client...")
    print("=" * 80)

    # Model options:
    # - llama-3.1-sonar-small-128k-online  (Fast, cost-effective, with search)
    # - llama-3.1-sonar-large-128k-online  (Balanced, with search)
    # - llama-3.1-sonar-huge-128k-online   (Best quality, with search)
    # - llama-3.1-8b-instruct              (Fast, no search)
    # - llama-3.1-70b-instruct             (High quality, no search)

    model_name = "llama-3.1-sonar-large-128k-online"

    try:
        model = init_model(
            backend="perplexity",
            model_path=model_name,
            config={"api_key": api_key},  # Optional, uses env var by default
        )
    except Exception as e:
        # Sanitize error message to avoid leaking sensitive information
        error_msg = str(e)
        if "api" in error_msg.lower() or "key" in error_msg.lower():
            print(
                "❌ Failed to initialize Perplexity: Authentication error. Please check your API key."
            )
        else:
            print("❌ Failed to initialize Perplexity: Connection or configuration error.")
        sys.exit(1)

    # Example 1: Simple question
    print("\n" + "=" * 80)
    print("Example 1: Simple Question")
    print("=" * 80)

    config = GenerationConfig(temperature=0.2, max_tokens=512, top_p=0.95)

    prompt = "What are the key differences between Python 3.11 and Python 3.12?"

    print(f"\n📝 Prompt: {prompt}")
    print("\n🤖 Generating response...")

    result = model.generate(
        prompt=prompt, config=config, system_prompt="You are a helpful Python expert assistant."
    )

    print(f"\n✅ Response ({result.tokens_generated} tokens):")
    print("-" * 80)
    print(result.text)
    print("-" * 80)
    print(f"Finish reason: {result.finish_reason}")
    print(
        f"Tokens: {result.prompt_tokens} prompt + {result.tokens_generated} generated = {result.total_tokens} total"
    )

    # Example 2: Real-time search with Perplexity (sonar models)
    if "sonar" in model_name:
        print("\n" + "=" * 80)
        print("Example 2: Real-time Search (Sonar models)")
        print("=" * 80)

        prompt = "What are the latest developments in AI safety research in 2025?"

        print(f"\n📝 Prompt: {prompt}")
        print("\n🔍 Searching and generating (using Perplexity's real-time search)...")

        result = model.generate(
            prompt=prompt,
            config=config,
            system_prompt="You are a knowledgeable AI researcher. Provide current, accurate information.",
        )

        print(f"\n✅ Response ({result.tokens_generated} tokens):")
        print("-" * 80)
        print(result.text)
        print("-" * 80)

    # Example 3: Code generation
    print("\n" + "=" * 80)
    print("Example 3: Code Generation")
    print("=" * 80)

    code_prompt = """
Write a Python function that:
1. Takes a list of numbers
2. Removes duplicates
3. Sorts in descending order
4. Returns the top 3 values

Include type hints and a docstring.
"""

    print(f"\n📝 Prompt: {code_prompt.strip()}")
    print("\n💻 Generating code...")

    result = model.generate(
        prompt=code_prompt,
        config=GenerationConfig(temperature=0.1, max_tokens=256),
        system_prompt="You are an expert Python developer. Write clean, well-documented code.",
    )

    print(f"\n✅ Response ({result.tokens_generated} tokens):")
    print("-" * 80)
    print(result.text)
    print("-" * 80)

    # Cleanup
    print("\n" + "=" * 80)
    print("Cleanup")
    print("=" * 80)
    model.unload()
    print("✓ Client unloaded")

    print("\n" + "=" * 80)
    print("Example completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
