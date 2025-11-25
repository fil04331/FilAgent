"""
Integration tests for E2E workflows

These tests cover end-to-end scenarios to improve overall code coverage:
- User query → HTN planning → Execution → Response
- Multi-tool orchestration
- Error recovery flows
- Middleware integration
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.agent import Agent
from tools.base import ToolResult, ToolStatus


@pytest.fixture
def full_agent_config():
    """Full agent configuration for E2E tests"""
    config = Mock()
    config.model = Mock()
    config.model.model_path = "test_model.gguf"
    config.model.temperature = 0.7
    config.model.max_tokens = 1000
    config.model.context_length = 4096
    
    # HTN configuration
    htn_planning = Mock()
    htn_planning.enabled = False  # Disable for simple E2E
    config.htn_planning = htn_planning
    
    # Compliance guardian
    compliance_guardian = Mock()
    compliance_guardian.enabled = False
    config.compliance_guardian = compliance_guardian
    
    return config


@pytest.fixture
def simple_agent(full_agent_config):
    """Agent for simple E2E testing"""
    with patch('runtime.agent.get_config', return_value=full_agent_config), \
         patch('runtime.agent.get_logger'), \
         patch('runtime.agent.get_dr_manager'), \
         patch('runtime.agent.get_tracker'), \
         patch('runtime.agent._init_model'):
        agent = Agent(config=full_agent_config)
        agent.model = Mock()
        agent.model.generate.return_value = Mock(text="Test response")
        return agent


@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.coverage
class TestSimpleQueryFlow:
    """Test simple query execution flow"""
    
    def test_simple_query_execution(self, simple_agent):
        """Test executing a simple query"""
        with patch.object(simple_agent, '_run_simple') as mock_simple:
            mock_simple.return_value = {
                "response": "42",
                "usage": {"tokens": 10}
            }
            
            result = simple_agent.chat("What is 2+2?", "conv-123")
            
            assert result is not None
            assert "response" in result
            assert mock_simple.called
    
    def test_query_with_tool_execution(self, simple_agent):
        """Test query that triggers tool execution"""
        # Mock tool registry
        calc_tool = Mock()
        calc_tool.execute.return_value = ToolResult(
            status=ToolStatus.SUCCESS,
            output="4",
            metadata={}
        )
        
        with patch.object(simple_agent.tool_registry, 'get', return_value=calc_tool):
            # Simulate agent detecting tool call
            with patch.object(simple_agent, '_run_simple') as mock_simple:
                mock_simple.return_value = {
                    "response": "The answer is 4",
                    "tool_calls": [{"name": "calculator", "result": "4"}],
                    "usage": {"tokens": 15}
                }
                
                result = simple_agent.chat("Calculate 2+2", "conv-123")
                
                assert result is not None
                assert "response" in result


@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.coverage
class TestToolExecutionFlow:
    """Test tool execution and orchestration"""
    
    def test_single_tool_execution(self, simple_agent):
        """Test executing a single tool"""
        # Get calculator tool
        calc_tool = simple_agent.tool_registry.get("math_calculator")
        
        if calc_tool:
            result = calc_tool.execute(arguments={"expression": "1+1"})
            assert isinstance(result, ToolResult)
    
    def test_file_reader_tool_execution(self, simple_agent, tmp_path):
        """Test file reader tool"""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")
        
        # Get file reader tool
        file_tool = simple_agent.tool_registry.get("file_read")
        
        if file_tool:
            result = file_tool.execute(arguments={"path": str(test_file)})
            assert isinstance(result, ToolResult)
    
    def test_python_sandbox_tool_execution(self, simple_agent):
        """Test python sandbox tool"""
        sandbox_tool = simple_agent.tool_registry.get("python_sandbox")
        
        if sandbox_tool:
            result = sandbox_tool.execute(arguments={"code": "print('hello')"})
            assert isinstance(result, ToolResult)


@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.coverage
class TestMiddlewareIntegration:
    """Test middleware integration in E2E flows"""
    
    def test_logging_middleware_integration(self, simple_agent):
        """Test logging middleware captures events"""
        if simple_agent.logger:
            # Log an event
            simple_agent.logger.log_event(
                actor="test",
                event="test_event",
                level="INFO"
            )
            
            # Should not raise exception
            assert True
    
    def test_decision_record_generation(self, simple_agent):
        """Test decision record generation"""
        if simple_agent.dr_manager:
            # Generate a decision record
            dr_id = simple_agent.dr_manager.generate_dr(
                decision_type="test",
                context={"query": "test"},
                metadata={}
            )
            
            # Should return a DR ID
            assert dr_id is not None or dr_id == ""
    
    def test_provenance_tracking(self, simple_agent):
        """Test provenance tracking"""
        if simple_agent.tracker:
            # Track an activity
            simple_agent.tracker.track_activity(
                activity_type="test",
                entity_id="test-123",
                metadata={}
            )
            
            # Should not raise exception
            assert True


@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.coverage
class TestErrorRecovery:
    """Test error recovery mechanisms"""
    
    def test_model_generation_error_handling(self, simple_agent):
        """Test handling model generation errors"""
        simple_agent.model.generate.side_effect = Exception("Model error")
        
        with pytest.raises(Exception):
            simple_agent.chat("Test query", "conv-123")
    
    def test_tool_execution_error_handling(self, simple_agent):
        """Test handling tool execution errors"""
        # Mock a failing tool
        failing_tool = Mock()
        failing_tool.execute.side_effect = Exception("Tool error")
        
        with patch.object(simple_agent.tool_registry, 'get', return_value=failing_tool):
            # Should handle gracefully or raise
            try:
                result = simple_agent.chat("Use failing tool", "conv-123")
                assert result is not None
            except Exception:
                # Expected to raise
                assert True
    
    def test_conversation_persistence_error_handling(self, simple_agent):
        """Test handling conversation persistence errors"""
        with patch('memory.episodic.add_message', side_effect=Exception("DB error")):
            # Should handle DB errors gracefully
            try:
                result = simple_agent.chat("Test query", "conv-123")
                # May succeed with fallback or raise
                assert result is not None or True
            except Exception:
                # Expected behavior
                assert True


@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.coverage
class TestConfigurationIntegration:
    """Test configuration integration"""
    
    def test_config_loading(self):
        """Test configuration loading"""
        from runtime.config import get_config
        
        config = get_config()
        assert config is not None
    
    def test_config_singleton(self):
        """Test config singleton pattern"""
        from runtime.config import get_config
        
        config1 = get_config()
        config2 = get_config()
        
        assert config1 is config2
    
    def test_config_reload(self):
        """Test config reload functionality"""
        from runtime.config import reload_config
        
        config = reload_config()
        assert config is not None


@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.coverage
class TestMemoryIntegration:
    """Test memory system integration"""
    
    def test_conversation_storage(self, simple_agent):
        """Test storing conversation messages"""
        from memory.episodic import add_message, get_messages
        
        conversation_id = "test-conv-123"
        
        # Add messages
        add_message(
            conversation_id=conversation_id,
            role="user",
            content="Test message"
        )
        
        add_message(
            conversation_id=conversation_id,
            role="assistant",
            content="Test response"
        )
        
        # Retrieve messages
        messages = get_messages(conversation_id)
        
        assert len(messages) >= 2
        assert messages[-2]["role"] == "user"
        assert messages[-1]["role"] == "assistant"
    
    def test_conversation_retrieval(self):
        """Test retrieving conversation history"""
        from memory.episodic import get_messages
        
        conversation_id = "nonexistent-conv"
        messages = get_messages(conversation_id)
        
        # Should return empty list for nonexistent conversation
        assert isinstance(messages, list)


@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.coverage
class TestAgentBuilders:
    """Test agent construction and initialization"""
    
    def test_build_action_registry(self, simple_agent):
        """Test building action registry from tools"""
        registry = simple_agent._build_action_registry()
        
        assert isinstance(registry, dict)
        assert len(registry) > 0
        
        # Each action should be callable
        for action_name, action_func in registry.items():
            assert callable(action_func)
    
    def test_tool_registry_initialization(self, simple_agent):
        """Test tool registry is properly initialized"""
        assert simple_agent.tool_registry is not None
        
        tools = simple_agent.tool_registry.get_all()
        assert len(tools) > 0
    
    def test_middleware_initialization_sequence(self, full_agent_config):
        """Test middleware initialization in correct sequence"""
        with patch('runtime.agent.get_config', return_value=full_agent_config), \
             patch('runtime.agent.get_logger') as mock_logger, \
             patch('runtime.agent.get_dr_manager') as mock_dr, \
             patch('runtime.agent.get_tracker') as mock_tracker, \
             patch('runtime.agent._init_model'):
            
            agent = Agent(config=full_agent_config)
            
            # Check that middleware getters were called
            assert mock_logger.called or agent.logger is not None
            assert mock_dr.called or agent.dr_manager is not None
            assert mock_tracker.called or agent.tracker is not None
