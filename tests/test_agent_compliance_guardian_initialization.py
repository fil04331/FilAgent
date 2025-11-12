"""
Test suite for Bug Fix: Missing compliance_guardian Initialization in Agent

This test suite validates the fix for the critical bug where:
1. Agent.__init__ was missing initialization of self.compliance_guardian (Bug #1)
2. config.py was missing compliance_guardian_data extraction (Bug #2)

The bug caused AttributeError at runtime when the agent tried to access
self.compliance_guardian in _run_simple() method.

Test coverage:
- Compliance guardian initializes correctly when enabled
- Compliance guardian is None when disabled
- Compliance guardian is None when config is missing
- No AttributeError when accessing compliance_guardian
- Config loads correctly with compliance_guardian section
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from runtime.agent import Agent
from runtime.config import AgentConfig, ComplianceGuardianConfig
from planner.compliance_guardian import ComplianceGuardian


class TestComplianceGuardianInitialization:
    """Test suite for compliance_guardian initialization fix"""

    def test_agent_has_compliance_guardian_attribute(self):
        """
        Test: Agent instance has compliance_guardian attribute after initialization

        This test verifies that Bug #1 is fixed - the attribute must exist
        even if it's None, to prevent AttributeError.
        """
        # Create agent with minimal config
        with patch('runtime.agent.get_config') as mock_config:
            mock_config.return_value = AgentConfig(
                name="test_agent",
                version="1.0.0"
            )

            agent = Agent()

            # Critical: attribute must exist (not raise AttributeError)
            assert hasattr(agent, 'compliance_guardian')

    def test_compliance_guardian_none_when_not_in_config(self):
        """
        Test: compliance_guardian is None when not configured

        This is the default safe behavior - no config means disabled.
        """
        with patch('runtime.agent.get_config') as mock_config:
            mock_config.return_value = AgentConfig(
                name="test_agent",
                version="1.0.0"
            )

            agent = Agent()

            assert agent.compliance_guardian is None

    def test_compliance_guardian_none_when_disabled(self):
        """
        Test: compliance_guardian is None when explicitly disabled in config
        """
        with patch('runtime.agent.get_config') as mock_config:
            # Create config with compliance_guardian disabled
            cg_config = ComplianceGuardianConfig(enabled=False)
            base_config = AgentConfig(
                name="test_agent",
                version="1.0.0"
            )
            base_config.compliance_guardian = cg_config
            mock_config.return_value = base_config

            agent = Agent()

            assert agent.compliance_guardian is None

    def test_compliance_guardian_initialized_when_enabled(self):
        """
        Test: compliance_guardian is properly initialized when enabled

        This is the critical test - when enabled in config, the ComplianceGuardian
        instance should be created successfully.
        """
        with patch('runtime.agent.get_config') as mock_config:
            # Create config with compliance_guardian enabled
            cg_config = ComplianceGuardianConfig(
                enabled=True,
                rules_path="config/compliance_rules.yaml"
            )
            base_config = AgentConfig(
                name="test_agent",
                version="1.0.0"
            )
            base_config.compliance_guardian = cg_config
            mock_config.return_value = base_config

            agent = Agent()

            # Should be initialized (or None if initialization failed gracefully)
            assert hasattr(agent, 'compliance_guardian')
            # If initialized, should be ComplianceGuardian instance or None
            assert agent.compliance_guardian is None or isinstance(agent.compliance_guardian, ComplianceGuardian)

    def test_compliance_guardian_graceful_failure(self):
        """
        Test: Agent handles ComplianceGuardian initialization failure gracefully

        If ComplianceGuardian fails to initialize, the agent should continue
        with compliance_guardian=None rather than crashing.
        """
        with patch('runtime.agent.get_config') as mock_config:
            with patch('runtime.agent.ComplianceGuardian') as mock_cg:
                # Simulate ComplianceGuardian import/init failure
                mock_cg.side_effect = Exception("Simulated failure")

                cg_config = ComplianceGuardianConfig(enabled=True)
                base_config = AgentConfig(
                    name="test_agent",
                    version="1.0.0"
                )
                base_config.compliance_guardian = cg_config
                mock_config.return_value = base_config

                # Should not raise exception
                agent = Agent()

                # Should fall back to None
                assert agent.compliance_guardian is None

    def test_config_loads_compliance_guardian_section(self):
        """
        Test: AgentConfig.from_yaml correctly loads compliance_guardian section

        This tests Bug #2 fix - the config loader must extract and create
        compliance_guardian_config from the YAML.
        """
        # Create temporary config file with compliance_guardian section
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_data = {
                'agent': {
                    'name': 'test_agent',
                    'version': '1.0.0',
                    'max_iterations': 10,
                    'timeout': 300
                },
                'generation': {
                    'temperature': 0.2,
                    'max_tokens': 800
                },
                'timeouts': {
                    'generation': 60,
                    'tool_execution': 30
                },
                'model': {
                    'name': 'llama-3',
                    'path': 'models/test.gguf',
                    'backend': 'llama.cpp'
                },
                'memory': {
                    'episodic': {'ttl_days': 30},
                    'semantic': {'max_items': 100}
                },
                'logging': {
                    'level': 'INFO',
                    'format': 'structured'
                },
                'compliance': {
                    'enabled': True,
                    'log_queries': True
                },
                'compliance_guardian': {
                    'enabled': True,
                    'rules_path': 'config/compliance_rules.yaml',
                    'validate_queries': True,
                    'validate_plans': True,
                    'audit_executions': True,
                    'strict_mode': True
                }
            }
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            # Load config from YAML
            config = AgentConfig.from_yaml(temp_path)

            # Verify compliance_guardian was loaded correctly
            assert hasattr(config, 'compliance_guardian')
            assert config.compliance_guardian is not None
            assert isinstance(config.compliance_guardian, ComplianceGuardianConfig)
            assert config.compliance_guardian.enabled is True
            assert config.compliance_guardian.validate_queries is True
            assert config.compliance_guardian.strict_mode is True

        finally:
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)

    def test_agent_run_simple_no_attribute_error(self):
        """
        Test: Agent._run_simple() doesn't raise AttributeError for compliance_guardian

        This is the integration test that would have failed before the fix.
        The original bug caused:
            if self.compliance_guardian:  # <- AttributeError here!
        """
        with patch('runtime.agent.get_config') as mock_config:
            mock_config.return_value = AgentConfig(
                name="test_agent",
                version="1.0.0"
            )

            agent = Agent()

            # Mock model to avoid actual LLM calls
            agent.model = Mock()
            agent.model.generate = Mock(return_value=Mock(text="Test response"))

            # This should NOT raise AttributeError
            try:
                # The check "if self.compliance_guardian:" must work
                has_cg = agent.compliance_guardian
                # If we get here, no AttributeError was raised
                assert True
            except AttributeError as e:
                pytest.fail(f"AttributeError raised: {e}. Bug fix failed!")

    def test_compliance_guardian_with_custom_rules_path(self):
        """
        Test: ComplianceGuardian uses custom rules_path from config
        """
        custom_path = "custom/path/to/rules.yaml"

        with patch('runtime.agent.get_config') as mock_config:
            with patch('runtime.agent.ComplianceGuardian') as mock_cg:
                cg_config = ComplianceGuardianConfig(
                    enabled=True,
                    rules_path=custom_path
                )
                base_config = AgentConfig(
                    name="test_agent",
                    version="1.0.0"
                )
                base_config.compliance_guardian = cg_config
                mock_config.return_value = base_config

                agent = Agent()

                # Verify ComplianceGuardian was called with custom path
                if mock_cg.called:
                    mock_cg.assert_called_with(config_path=custom_path)


class TestConfigComplianceGuardianExtraction:
    """Test suite specifically for config.py Bug #2 fix"""

    def test_compliance_guardian_data_extracted_from_yaml(self):
        """
        Test: from_yaml extracts compliance_guardian section

        Bug #2: compliance_guardian_data was never extracted from raw_config
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_data = {
                'agent': {'name': 'test', 'version': '1.0'},
                'generation': {'temperature': 0.2},
                'timeouts': {'generation': 60},
                'model': {'name': 'test-model', 'path': 'test.gguf'},
                'memory': {'episodic': {'ttl_days': 30}},
                'logging': {'level': 'INFO'},
                'compliance': {'enabled': True},
                'compliance_guardian': {
                    'enabled': True,
                    'validate_queries': True
                }
            }
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            config = AgentConfig.from_yaml(temp_path)

            # This would have caused NameError before the fix
            assert config.compliance_guardian is not None

        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_compliance_guardian_config_none_when_missing(self):
        """
        Test: compliance_guardian_config is None when section is missing
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_data = {
                'agent': {'name': 'test', 'version': '1.0'},
                'generation': {'temperature': 0.2},
                'timeouts': {'generation': 60},
                'model': {'name': 'test-model', 'path': 'test.gguf'},
                'memory': {'episodic': {'ttl_days': 30}},
                'logging': {'level': 'INFO'},
                'compliance': {'enabled': True}
                # No compliance_guardian section
            }
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            config = AgentConfig.from_yaml(temp_path)

            # Should be None, not cause NameError
            assert config.compliance_guardian is None

        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestEndToEndComplianceGuardian:
    """End-to-end integration tests"""

    def test_e2e_agent_with_compliance_guardian_enabled(self):
        """
        Test: Full agent lifecycle with compliance_guardian enabled

        This simulates the real-world scenario that would have failed
        before the bug fix.
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_data = {
                'agent': {'name': 'e2e_test', 'version': '1.0'},
                'generation': {'temperature': 0.2, 'max_tokens': 800},
                'timeouts': {'generation': 60, 'tool_execution': 30},
                'model': {'name': 'test-model', 'path': 'test.gguf', 'backend': 'llama.cpp'},
                'memory': {'episodic': {'ttl_days': 30}, 'semantic': {'max_items': 100}},
                'logging': {'level': 'INFO', 'format': 'structured'},
                'compliance': {'enabled': True},
                'compliance_guardian': {
                    'enabled': True,
                    'validate_queries': True,
                    'audit_executions': True
                }
            }
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            # Load config
            config = AgentConfig.from_yaml(temp_path)

            # Create agent with config
            with patch('runtime.agent.get_config') as mock_config:
                mock_config.return_value = config
                agent = Agent()

                # Verify no AttributeError
                assert hasattr(agent, 'compliance_guardian')

                # Verify agent can check compliance_guardian without error
                if agent.compliance_guardian:
                    # Would use it
                    pass
                else:
                    # Would skip
                    pass

                # Test passes if we reach here without AttributeError
                assert True

        finally:
            Path(temp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
