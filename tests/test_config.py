"""
Tests for configuration management and persistence
"""
import pytest
import yaml
import tempfile
import os
from pathlib import Path
from runtime.config import (
    AgentConfig,
    GenerationConfig,
    TimeoutConfig,
    ModelConfig,
    MemoryConfig,
    LoggingConfig,
    ComplianceConfig,
    AgentRuntimeSettings,
    HTNPlanningConfig,
    HTNExecutionConfig,
    HTNVerificationConfig,
)


class TestConfigPersistence:
    """Tests for configuration save/load persistence"""

    def test_save_and_load_basic_config(self):
        """Test that a basic config can be saved and loaded back"""
        # Create a temporary directory for test config
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_agent.yaml"

            # Create a config with specific values
            original_config = AgentConfig(
                name="test_agent",
                version="1.0.0",
                generation=GenerationConfig(
                    temperature=0.5,
                    top_p=0.9,
                    max_tokens=1000,
                    seed=123,
                ),
                timeouts=TimeoutConfig(
                    generation=90,
                    tool_execution=45,
                    total_request=400,
                ),
                runtime_settings=AgentRuntimeSettings(
                    max_iterations=15,
                    timeout=400,
                ),
            )

            # Save the config
            original_config.save(str(config_path))

            # Verify file was created
            assert config_path.exists(), "Config file should be created"

            # Load it back
            loaded_config = AgentConfig.load(str(tmpdir))

            # Verify all values match
            assert loaded_config.name == original_config.name
            assert loaded_config.version == original_config.version
            assert loaded_config.generation.temperature == original_config.generation.temperature
            assert loaded_config.generation.top_p == original_config.generation.top_p
            assert loaded_config.generation.max_tokens == original_config.generation.max_tokens
            assert loaded_config.generation.seed == original_config.generation.seed
            assert loaded_config.timeouts.generation == original_config.timeouts.generation
            assert loaded_config.timeouts.tool_execution == original_config.timeouts.tool_execution
            assert loaded_config.timeouts.total_request == original_config.timeouts.total_request
            assert loaded_config.runtime_settings.max_iterations == original_config.runtime_settings.max_iterations
            assert loaded_config.runtime_settings.timeout == original_config.runtime_settings.timeout

    def test_save_and_load_with_htn_configs(self):
        """Test that config with HTN settings can be saved and loaded"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_agent.yaml"

            # Create config with HTN settings
            original_config = AgentConfig(
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
                    task_timeout_sec=120,
                ),
                htn_verification=HTNVerificationConfig(
                    default_level="paranoid",
                    custom_verifiers=["verifier1", "verifier2"],
                ),
            )

            # Save and load
            original_config.save(str(config_path))
            loaded_config = AgentConfig.load(str(tmpdir))

            # Verify HTN configs
            assert loaded_config.htn_planning is not None
            assert loaded_config.htn_planning.enabled == original_config.htn_planning.enabled
            assert loaded_config.htn_planning.default_strategy == original_config.htn_planning.default_strategy
            assert loaded_config.htn_planning.max_decomposition_depth == original_config.htn_planning.max_decomposition_depth

            assert loaded_config.htn_execution is not None
            assert loaded_config.htn_execution.default_strategy == original_config.htn_execution.default_strategy
            assert loaded_config.htn_execution.max_parallel_workers == original_config.htn_execution.max_parallel_workers
            assert loaded_config.htn_execution.task_timeout_sec == original_config.htn_execution.task_timeout_sec

            assert loaded_config.htn_verification is not None
            assert loaded_config.htn_verification.default_level == original_config.htn_verification.default_level
            assert loaded_config.htn_verification.custom_verifiers == original_config.htn_verification.custom_verifiers

    def test_save_and_load_memory_config(self):
        """Test that memory configuration persists correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_agent.yaml"

            # Create config with custom memory settings
            original_config = AgentConfig(
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
            original_config.save(str(config_path))
            loaded_config = AgentConfig.load(str(tmpdir))

            # Verify memory config
            assert loaded_config.memory.episodic_ttl_days == 60
            assert loaded_config.memory.episodic_max_conversations == 2000
            assert loaded_config.memory.semantic_rebuild_days == 7
            assert loaded_config.memory.semantic_max_items == 5000
            assert loaded_config.memory.semantic_similarity_threshold == 0.85

    def test_save_and_load_compliance_config(self):
        """Test that compliance configuration persists correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_agent.yaml"

            # Create config with compliance settings
            original_config = AgentConfig(
                name="compliance_test",
                version="1.0.0",
                compliance=ComplianceConfig(
                    worm_enabled=False,
                    dr_required_for=["write_file", "delete_file"],
                    pii_redaction=True,
                    provenance_tracking=False,
                ),
            )

            # Save and load
            original_config.save(str(config_path))
            loaded_config = AgentConfig.load(str(tmpdir))

            # Verify compliance config
            assert loaded_config.compliance.worm_enabled == False
            assert loaded_config.compliance.dr_required_for == ["write_file", "delete_file"]
            assert loaded_config.compliance.pii_redaction == True
            assert loaded_config.compliance.provenance_tracking is False

    def test_save_creates_directory_if_not_exists(self):
        """Test that save creates parent directories if needed"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use a nested path that doesn't exist yet
            config_path = Path(tmpdir) / "nested" / "config" / "agent.yaml"

            config = AgentConfig(name="test", version="1.0.0")

            # Save should create the directories
            config.save(str(config_path))

            # Verify directory was created and file exists
            assert config_path.parent.exists()
            assert config_path.exists()

    def test_save_overwrites_existing_file(self):
        """Test that save overwrites existing config file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_agent.yaml"

            # Create and save first config
            config1 = AgentConfig(
                name="first_agent",
                version="1.0.0",
                runtime_settings=AgentRuntimeSettings(max_iterations=5),
            )
            config1.save(str(config_path))

            # Create and save second config with different values
            config2 = AgentConfig(
                name="second_agent",
                version="2.0.0",
                runtime_settings=AgentRuntimeSettings(max_iterations=20),
            )
            config2.save(str(config_path))

            # Load and verify it has the second config's values
            loaded_config = AgentConfig.load(str(tmpdir))
            assert loaded_config.name == "second_agent"
            assert loaded_config.version == "2.0.0"
            assert loaded_config.runtime_settings.max_iterations == 20

    def test_yaml_structure_is_valid(self):
        """Test that saved YAML has the correct structure"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_agent.yaml"

            config = AgentConfig(
                name="test_agent",
                version="1.0.0",
                htn_planning=HTNPlanningConfig(enabled=True),
            )
            config.save(str(config_path))

            # Load the raw YAML and verify structure
            with open(config_path, 'r') as f:
                yaml_data = yaml.safe_load(f)

            # Verify top-level keys exist
            assert 'agent' in yaml_data
            assert 'generation' in yaml_data
            assert 'timeouts' in yaml_data
            assert 'model' in yaml_data
            assert 'memory' in yaml_data
            assert 'logging' in yaml_data
            assert 'compliance' in yaml_data
            assert 'htn_planning' in yaml_data

            # Verify memory has nested structure
            assert 'episodic' in yaml_data['memory']
            assert 'semantic' in yaml_data['memory']
            assert 'ttl_days' in yaml_data['memory']['episodic']
            assert 'max_conversations' in yaml_data['memory']['episodic']
            assert 'rebuild_days' in yaml_data['memory']['semantic']
            assert 'max_items' in yaml_data['memory']['semantic']
            assert 'similarity_threshold' in yaml_data['memory']['semantic']

    def test_config_without_optional_htn_configs(self):
        """Test that configs without HTN settings save and load correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_agent.yaml"

            # Create config without HTN settings (all None)
            original_config = AgentConfig(
                name="no_htn",
                version="1.0.0",
                htn_planning=None,
                htn_execution=None,
                htn_verification=None,
            )

            # Save and load
            original_config.save(str(config_path))

            # Load the raw YAML and verify HTN keys are not present
            with open(config_path, 'r') as f:
                yaml_data = yaml.safe_load(f)

            assert 'htn_planning' not in yaml_data
            assert 'htn_execution' not in yaml_data
            assert 'htn_verification' not in yaml_data

            # Load and verify
            loaded_config = AgentConfig.load(str(tmpdir))
            assert loaded_config.name == "no_htn"
            assert loaded_config.htn_planning is None
            assert loaded_config.htn_execution is None
            assert loaded_config.htn_verification is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
