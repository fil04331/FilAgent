#!/usr/bin/env python3
"""
Simple standalone test for configuration persistence
Can be run without pytest
"""
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.config import (
    AgentConfig,
    GenerationConfig,
    TimeoutConfig,
    AgentRuntimeSettings,
    HTNPlanningConfig,
    HTNExecutionConfig,
    HTNVerificationConfig,
    MemoryConfig,
)


def test_basic_save_and_load():
    """Test basic config save and load"""
    print("Testing basic save and load...")

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test_agent.yaml"

        # Create config
        original = AgentConfig(
            name="test_agent",
            version="1.0.0",
            generation=GenerationConfig(
                temperature=0.5,
                max_tokens=1000,
            ),
            runtime_settings=AgentRuntimeSettings(
                max_iterations=15,
                timeout=400,
            ),
        )

        # Save
        original.save(str(config_path))
        assert config_path.exists(), "Config file should exist"

        # Load
        loaded = AgentConfig.load(str(tmpdir))

        # Verify
        assert loaded.name == "test_agent"
        assert loaded.version == "1.0.0"
        assert loaded.generation.temperature == 0.5
        assert loaded.generation.max_tokens == 1000
        assert loaded.runtime_settings.max_iterations == 15
        assert loaded.runtime_settings.timeout == 400

    print("✓ Basic save and load test passed")


def test_htn_config_persistence():
    """Test HTN config persistence"""
    print("Testing HTN config persistence...")

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test_agent.yaml"

        # Create config with HTN
        original = AgentConfig(
            name="htn_agent",
            version="2.0.0",
            htn_planning=HTNPlanningConfig(
                enabled=True,
                default_strategy="hybrid",
                max_decomposition_depth=5,
            ),
            htn_execution=HTNExecutionConfig(
                default_strategy="parallel",
                max_parallel_workers=8,
            ),
            htn_verification=HTNVerificationConfig(
                default_level="paranoid",
                custom_verifiers=["v1", "v2"],
            ),
        )

        # Save and load
        original.save(str(config_path))
        loaded = AgentConfig.load(str(tmpdir))

        # Verify HTN configs
        assert loaded.htn_planning is not None
        assert loaded.htn_planning.enabled
        assert loaded.htn_planning.default_strategy == "hybrid"
        assert loaded.htn_planning.max_decomposition_depth == 5

        assert loaded.htn_execution is not None
        assert loaded.htn_execution.default_strategy == "parallel"
        assert loaded.htn_execution.max_parallel_workers == 8

        assert loaded.htn_verification is not None
        assert loaded.htn_verification.default_level == "paranoid"
        assert loaded.htn_verification.custom_verifiers == ["v1", "v2"]

    print("✓ HTN config persistence test passed")


def test_memory_config_persistence():
    """Test memory config persistence"""
    print("Testing memory config persistence...")

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test_agent.yaml"

        # Create config with custom memory settings
        original = AgentConfig(
            name="memory_test",
            version="1.0.0",
            memory=MemoryConfig(
                episodic_ttl_days=60,
                episodic_max_conversations=2000,
                semantic_rebuild_days=7,
                semantic_max_items=5000,
                semantic_similarity_threshold=0.85,
            ),
        )

        # Save and load
        original.save(str(config_path))
        loaded = AgentConfig.load(str(tmpdir))

        # Verify
        assert loaded.memory.episodic_ttl_days == 60
        assert loaded.memory.episodic_max_conversations == 2000
        assert loaded.memory.semantic_rebuild_days == 7
        assert loaded.memory.semantic_max_items == 5000
        assert loaded.memory.semantic_similarity_threshold == 0.85

    print("✓ Memory config persistence test passed")


def test_directory_creation():
    """Test that save creates directories"""
    print("Testing directory creation...")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Use nested path that doesn't exist
        config_path = Path(tmpdir) / "nested" / "config" / "agent.yaml"

        config = AgentConfig(name="test", version="1.0.0")
        config.save(str(config_path))

        # Verify
        assert config_path.parent.exists()
        assert config_path.exists()

    print("✓ Directory creation test passed")


def test_overwrite_existing():
    """Test overwriting existing config"""
    print("Testing overwrite existing...")

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test_agent.yaml"

        # First config
        config1 = AgentConfig(
            name="first",
            version="1.0.0",
            runtime_settings=AgentRuntimeSettings(max_iterations=5),
        )
        config1.save(str(config_path))

        # Second config
        config2 = AgentConfig(
            name="second",
            version="2.0.0",
            runtime_settings=AgentRuntimeSettings(max_iterations=20),
        )
        config2.save(str(config_path))

        # Load and verify
        loaded = AgentConfig.load(str(tmpdir))
        assert loaded.name == "second"
        assert loaded.version == "2.0.0"
        assert loaded.runtime_settings.max_iterations == 20

    print("✓ Overwrite existing test passed")


def test_without_htn_configs():
    """Test config without HTN settings"""
    print("Testing config without HTN settings...")

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test_agent.yaml"

        # Create config without HTN
        original = AgentConfig(
            name="no_htn",
            version="1.0.0",
            htn_planning=None,
            htn_execution=None,
            htn_verification=None,
        )

        # Save and load
        original.save(str(config_path))
        loaded = AgentConfig.load(str(tmpdir))

        # Verify
        assert loaded.name == "no_htn"
        assert loaded.htn_planning is None
        assert loaded.htn_execution is None
        assert loaded.htn_verification is None

    print("✓ Config without HTN test passed")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Running Configuration Persistence Tests")
    print("=" * 60)
    print()

    tests = [
        test_basic_save_and_load,
        test_htn_config_persistence,
        test_memory_config_persistence,
        test_directory_creation,
        test_overwrite_existing,
        test_without_htn_configs,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
            import traceback
            traceback.print_exc()

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
