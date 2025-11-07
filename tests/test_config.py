"""
Tests for runtime.config module
Focus on configuration serialization and the to_dict() method
"""
import pytest
from runtime.config import AgentConfig, MemoryConfig


class TestMemoryConfigToDictDynamic:
    """Test the dynamic to_dict() method for AgentConfig"""

    def test_to_dict_returns_dict(self):
        """Test that to_dict() returns a dictionary"""
        config = AgentConfig()
        result = config.to_dict()
        assert isinstance(result, dict)

    def test_to_dict_has_all_required_keys(self):
        """Test that to_dict() includes all required top-level keys"""
        config = AgentConfig()
        result = config.to_dict()
        
        required_keys = ['agent', 'generation', 'timeouts', 'model', 'memory', 'logging', 'compliance']
        for key in required_keys:
            assert key in result, f"Missing required key: {key}"

    def test_memory_dict_structure(self):
        """Test that memory is properly structured with episodic and semantic sections"""
        config = AgentConfig()
        result = config.to_dict()
        
        assert 'memory' in result
        assert isinstance(result['memory'], dict)
        assert 'episodic' in result['memory']
        assert 'semantic' in result['memory']
        assert isinstance(result['memory']['episodic'], dict)
        assert isinstance(result['memory']['semantic'], dict)

    def test_episodic_fields_mapped_correctly(self):
        """Test that episodic_* fields are correctly mapped to episodic section"""
        config = AgentConfig()
        result = config.to_dict()
        
        episodic = result['memory']['episodic']
        
        # Check that episodic fields are present without the prefix
        assert 'ttl_days' in episodic
        assert 'max_conversations' in episodic
        
        # Verify values match the config
        assert episodic['ttl_days'] == config.memory.episodic_ttl_days
        assert episodic['max_conversations'] == config.memory.episodic_max_conversations

    def test_semantic_fields_mapped_correctly(self):
        """Test that semantic_* fields are correctly mapped to semantic section"""
        config = AgentConfig()
        result = config.to_dict()
        
        semantic = result['memory']['semantic']
        
        # Check that semantic fields are present without the prefix
        assert 'rebuild_days' in semantic
        assert 'max_items' in semantic
        assert 'similarity_threshold' in semantic
        
        # Verify values match the config
        assert semantic['rebuild_days'] == config.memory.semantic_rebuild_days
        assert semantic['max_items'] == config.memory.semantic_max_items
        assert semantic['similarity_threshold'] == config.memory.semantic_similarity_threshold

    def test_agent_section_structure(self):
        """Test that agent section contains correct fields"""
        config = AgentConfig()
        result = config.to_dict()
        
        agent = result['agent']
        assert 'name' in agent
        assert 'version' in agent
        assert 'max_iterations' in agent
        assert 'timeout' in agent
        
        # Verify values
        assert agent['name'] == config.name
        assert agent['version'] == config.version
        assert agent['max_iterations'] == config.runtime_settings.max_iterations
        assert agent['timeout'] == config.runtime_settings.timeout

    def test_to_dict_adapts_to_new_memory_fields(self):
        """Test that the dynamic approach would handle new memory fields"""
        # This test verifies the introspection approach
        config = AgentConfig()
        
        # Get all field names from MemoryConfig
        memory_fields = config.memory.model_fields.keys()
        
        # Verify we have the expected prefixes
        episodic_fields = [f for f in memory_fields if f.startswith('episodic_')]
        semantic_fields = [f for f in memory_fields if f.startswith('semantic_')]
        
        assert len(episodic_fields) > 0, "Should have episodic fields"
        assert len(semantic_fields) > 0, "Should have semantic fields"
        
        # Verify to_dict() includes all of them
        result = config.to_dict()
        
        for field_name in episodic_fields:
            key = field_name.removeprefix('episodic_')
            assert key in result['memory']['episodic'], f"Missing episodic field: {key}"
        
        for field_name in semantic_fields:
            key = field_name.removeprefix('semantic_')
            assert key in result['memory']['semantic'], f"Missing semantic field: {key}"

    def test_htn_configs_included_when_present(self):
        """Test that optional HTN configurations are included when set"""
        from runtime.config import HTNPlanningConfig, HTNExecutionConfig, HTNVerificationConfig
        
        config = AgentConfig(
            htn_planning=HTNPlanningConfig(),
            htn_execution=HTNExecutionConfig(),
            htn_verification=HTNVerificationConfig()
        )
        
        result = config.to_dict()
        
        assert 'htn_planning' in result
        assert 'htn_execution' in result
        assert 'htn_verification' in result

    def test_htn_configs_excluded_when_none(self):
        """Test that optional HTN configurations are excluded when None"""
        config = AgentConfig()
        result = config.to_dict()
        
        # By default, HTN configs should be None
        if config.htn_planning is None:
            assert 'htn_planning' not in result
        if config.htn_execution is None:
            assert 'htn_execution' not in result
        if config.htn_verification is None:
            assert 'htn_verification' not in result

    def test_custom_memory_values(self):
        """Test that custom memory values are correctly reflected in to_dict()"""
        custom_memory = MemoryConfig(
            episodic_ttl_days=60,
            episodic_max_conversations=2000,
            semantic_rebuild_days=7,
            semantic_max_items=5000,
            semantic_similarity_threshold=0.85
        )
        
        config = AgentConfig(memory=custom_memory)
        result = config.to_dict()
        
        assert result['memory']['episodic']['ttl_days'] == 60
        assert result['memory']['episodic']['max_conversations'] == 2000
        assert result['memory']['semantic']['rebuild_days'] == 7
        assert result['memory']['semantic']['max_items'] == 5000
        assert result['memory']['semantic']['similarity_threshold'] == 0.85


class TestAgentConfigSave:
    """Test the save() method implementation"""

    def test_save_creates_yaml_file(self, tmp_path):
        """Test that save() creates a YAML file"""
        import yaml
        
        config = AgentConfig()
        save_path = tmp_path / "test_config.yaml"
        
        config.save(str(save_path))
        
        assert save_path.exists()
        
        # Verify it's valid YAML
        with open(save_path, 'r') as f:
            loaded = yaml.safe_load(f)
        
        assert isinstance(loaded, dict)

    def test_save_creates_parent_directories(self, tmp_path):
        """Test that save() creates parent directories if they don't exist"""
        config = AgentConfig()
        save_path = tmp_path / "nested" / "dir" / "config.yaml"
        
        config.save(str(save_path))
        
        assert save_path.exists()

    def test_saved_yaml_has_correct_structure(self, tmp_path):
        """Test that saved YAML has the correct structure"""
        import yaml
        
        config = AgentConfig()
        save_path = tmp_path / "test_config.yaml"
        
        config.save(str(save_path))
        
        with open(save_path, 'r') as f:
            loaded = yaml.safe_load(f)
        
        # Verify structure matches to_dict()
        expected = config.to_dict()
        
        assert loaded['agent'] == expected['agent']
        assert loaded['memory']['episodic'] == expected['memory']['episodic']
        assert loaded['memory']['semantic'] == expected['memory']['semantic']
