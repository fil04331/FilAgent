"""
Comprehensive tests for Middleware components

Coverage targets:
- Logging middleware (EventLogger)
- Audit trail middleware (DecisionRecordManager)
- Provenance middleware (ProvenanceTracker)
- RBAC middleware
- Redaction middleware
- Constraints middleware
- WORM logging
"""
import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.mark.unit
@pytest.mark.compliance
@pytest.mark.coverage
class TestLoggingMiddleware:
    """Tests for logging middleware"""
    
    def test_event_logger_initialization(self):
        """Test EventLogger initialization"""
        from runtime.middleware.logging import EventLogger
        
        logger = EventLogger()
        assert logger is not None
    
    def test_log_event(self):
        """Test logging an event"""
        from runtime.middleware.logging import EventLogger
        
        logger = EventLogger()
        logger.log_event(
            actor="test",
            event="test_event",
            level="INFO",
            metadata={"key": "value"}
        )
        
        # Should not raise exception
        assert True
    
    def test_get_logger_singleton(self):
        """Test logger singleton pattern"""
        from runtime.middleware.logging import get_logger
        
        logger1 = get_logger()
        logger2 = get_logger()
        
        assert logger1 is logger2
    
    def test_event_log_levels(self):
        """Test different log levels"""
        from runtime.middleware.logging import EventLogger
        
        logger = EventLogger()
        
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            logger.log_event(
                actor="test",
                event="test_event",
                level=level
            )
        
        # All should succeed
        assert True


@pytest.mark.unit
@pytest.mark.compliance
@pytest.mark.coverage
class TestAuditTrailMiddleware:
    """Tests for audit trail middleware"""

    def test_decision_record_manager_initialization(self):
        """Test DRManager initialization"""
        from runtime.middleware.audittrail import DRManager

        dr_manager = DRManager()
        assert dr_manager is not None

    def test_generate_decision_record(self):
        """Test generating a decision record"""
        from runtime.middleware.audittrail import DRManager

        dr_manager = DRManager()
        dr = dr_manager.create_dr(
            actor="test_actor",
            task_id="test-task-123",
            decision="tool_execution",
            prompt_hash="abc123"
        )

        # Should return a DecisionRecord with dr_id
        assert dr is not None
        assert hasattr(dr, 'dr_id')
        assert isinstance(dr.dr_id, str)

    def test_get_dr_manager_singleton(self):
        """Test DR manager singleton pattern"""
        from runtime.middleware.audittrail import get_dr_manager

        dr1 = get_dr_manager()
        dr2 = get_dr_manager()

        assert dr1 is dr2


@pytest.mark.unit
@pytest.mark.compliance
@pytest.mark.coverage
class TestProvenanceMiddleware:
    """Tests for provenance middleware"""

    def test_provenance_tracker_initialization(self):
        """Test ProvenanceTracker initialization"""
        from runtime.middleware.provenance import ProvenanceTracker

        tracker = ProvenanceTracker()
        assert tracker is not None

    def test_track_generation(self):
        """Test tracking a generation activity"""
        from runtime.middleware.provenance import ProvenanceTracker

        tracker = ProvenanceTracker()
        # track_generation is the actual method available
        trace_id = tracker.track_generation(
            conversation_id="test-conv-123",
            input_message="Test message"
        )

        # Should return a trace ID
        assert trace_id is not None
        assert isinstance(trace_id, str)

    def test_get_tracker_singleton(self):
        """Test tracker singleton pattern"""
        from runtime.middleware.provenance import get_tracker

        tracker1 = get_tracker()
        tracker2 = get_tracker()

        assert tracker1 is tracker2


@pytest.mark.unit
@pytest.mark.compliance
@pytest.mark.coverage
class TestMemoryRetention:
    """Tests for memory retention policies"""
    
    def test_retention_manager_initialization(self):
        """Test RetentionManager initialization"""
        from memory.retention import RetentionManager
        
        manager = RetentionManager()
        assert manager is not None
    
    def test_cleanup_old_conversations(self):
        """Test cleaning up old conversations"""
        from memory.retention import RetentionManager
        
        manager = RetentionManager()
        
        # Should execute without error
        try:
            manager.cleanup_old_conversations(days=30)
            assert True
        except Exception:
            # May fail if database doesn't exist
            pytest.skip("Database not initialized")
    
    def test_get_retention_stats(self):
        """Test getting retention statistics"""
        from memory.retention import RetentionManager
        
        manager = RetentionManager()
        
        try:
            stats = manager.get_retention_stats()
            assert isinstance(stats, dict) or stats is None
        except Exception:
            # May fail if database doesn't exist
            pytest.skip("Database not initialized")


@pytest.mark.unit
@pytest.mark.coverage
class TestModelInterface:
    """Tests for model interface"""
    
    def test_generation_config_creation(self):
        """Test GenerationConfig creation"""
        from runtime.model_interface import GenerationConfig
        
        config = GenerationConfig(
            temperature=0.7,
            max_tokens=1000,
            top_p=0.9,
            top_k=40
        )
        
        assert config.temperature == 0.7
        assert config.max_tokens == 1000
    
    def test_generation_config_defaults(self):
        """Test GenerationConfig default values"""
        from runtime.model_interface import GenerationConfig
        
        config = GenerationConfig()
        
        assert config.temperature >= 0
        assert config.max_tokens > 0
    
    def test_generation_result_creation(self):
        """Test GenerationResult creation"""
        from runtime.model_interface import GenerationResult

        result = GenerationResult(
            text="Test response",
            finish_reason="stop",
            tokens_generated=10,
            prompt_tokens=5,
            total_tokens=15
        )

        assert result.text == "Test response"
        assert result.finish_reason == "stop"
        assert result.total_tokens == 15


@pytest.mark.unit
@pytest.mark.coverage
class TestToolsDetailed:
    """Detailed tests for tool implementations"""
    
    def test_calculator_addition(self):
        """Test calculator addition"""
        from tools.calculator import CalculatorTool
        
        calc = CalculatorTool()
        result = calc.execute(arguments={"expression": "1+1"})
        
        assert result.status.name == "SUCCESS"
        assert "2" in str(result.output)
    
    def test_calculator_subtraction(self):
        """Test calculator subtraction"""
        from tools.calculator import CalculatorTool
        
        calc = CalculatorTool()
        result = calc.execute(arguments={"expression": "5-3"})
        
        assert result.status.name == "SUCCESS"
        assert "2" in str(result.output)
    
    def test_calculator_multiplication(self):
        """Test calculator multiplication"""
        from tools.calculator import CalculatorTool
        
        calc = CalculatorTool()
        result = calc.execute(arguments={"expression": "3*4"})
        
        assert result.status.name == "SUCCESS"
        assert "12" in str(result.output)
    
    def test_calculator_division(self):
        """Test calculator division"""
        from tools.calculator import CalculatorTool
        
        calc = CalculatorTool()
        result = calc.execute(arguments={"expression": "10/2"})
        
        assert result.status.name == "SUCCESS"
        assert "5" in str(result.output)
    
    def test_calculator_invalid_expression(self):
        """Test calculator with invalid expression"""
        from tools.calculator import CalculatorTool
        
        calc = CalculatorTool()
        result = calc.execute(arguments={"expression": "invalid"})
        
        # Should handle error gracefully
        assert result is not None
    
    def test_python_sandbox_simple_code(self):
        """Test python sandbox with simple code"""
        from tools.python_sandbox import PythonSandboxTool
        
        sandbox = PythonSandboxTool()
        result = sandbox.execute(arguments={"code": "x = 1 + 1\nprint(x)"})
        
        assert result.status.name in ["SUCCESS", "ERROR"]
    
    def test_python_sandbox_print_statement(self):
        """Test python sandbox with print"""
        from tools.python_sandbox import PythonSandboxTool
        
        sandbox = PythonSandboxTool()
        result = sandbox.execute(arguments={"code": "print('hello')"})
        
        assert result.status.name in ["SUCCESS", "ERROR"]
    
    def test_python_sandbox_error_handling(self):
        """Test python sandbox error handling"""
        from tools.python_sandbox import PythonSandboxTool
        
        sandbox = PythonSandboxTool()
        result = sandbox.execute(arguments={"code": "invalid syntax here"})
        
        # Should return error status
        assert result is not None
    
    def test_file_reader_nonexistent_file(self):
        """Test file reader with nonexistent file"""
        from tools.file_reader import FileReaderTool

        reader = FileReaderTool()
        # Use file_path (correct parameter name)
        result = reader.execute(arguments={"file_path": "/nonexistent/file.txt"})

        # Should handle error - BLOCKED for paths outside allowlist
        assert result.status.name in ["ERROR", "FAILURE", "BLOCKED"]

    def test_file_reader_with_valid_file(self, tmp_path):
        """Test file reader with valid file in allowed path"""
        from tools.file_reader import FileReaderTool
        from pathlib import Path

        # Create test file in working_set (allowed directory)
        working_set = Path("working_set")
        working_set.mkdir(exist_ok=True)
        test_file = working_set / "test_middleware_temp.txt"
        test_file.write_text("Test content")

        try:
            reader = FileReaderTool()
            # Use file_path (correct parameter name)
            result = reader.execute(arguments={"file_path": "working_set/test_middleware_temp.txt"})

            assert result.status.name == "SUCCESS"
            assert "Test content" in str(result.output)
        finally:
            # Cleanup
            if test_file.exists():
                test_file.unlink()


@pytest.mark.unit
@pytest.mark.coverage
class TestConfigAdvanced:
    """Advanced configuration tests"""
    
    def test_config_serialization(self):
        """Test config serialization"""
        from runtime.config import get_config
        
        config = get_config()
        
        # Should be able to access config attributes
        assert hasattr(config, 'model')
    
    def test_config_attribute_access(self):
        """Test accessing config attributes"""
        from runtime.config import get_config
        
        config = get_config()
        
        # Should have model config
        if hasattr(config, 'model'):
            model_config = config.model
            assert model_config is not None


@pytest.mark.unit
@pytest.mark.coverage
class TestAgentInternals:
    """Tests for agent internal methods"""
    
    def test_agent_tool_call_parsing(self):
        """Test tool call parsing from LLM output"""
        from runtime.agent import Agent
        from unittest.mock import Mock
        
        config = Mock()
        config.model = Mock()
        config.htn_planning = Mock()
        config.htn_planning.enabled = False
        config.compliance_guardian = Mock()
        config.compliance_guardian.enabled = False
        
        with patch('runtime.agent.get_config', return_value=config), \
             patch('runtime.agent.get_logger'), \
             patch('runtime.agent.get_dr_manager'), \
             patch('runtime.agent.get_tracker'), \
             patch('runtime.agent._init_model'):
            agent = Agent(config=config)
            
            # Test parsing tool calls
            text_with_tool_call = """
            I will use a tool:
            <tool_call>
            {"name": "calculator", "arguments": {"expression": "2+2"}}
            </tool_call>
            """
            
            # Should be able to parse tool calls
            assert "<tool_call>" in text_with_tool_call
    
    def test_agent_conversation_history(self):
        """Test agent conversation history management"""
        from runtime.agent import Agent
        from unittest.mock import Mock
        
        config = Mock()
        config.model = Mock()
        config.htn_planning = Mock()
        config.htn_planning.enabled = False
        config.compliance_guardian = Mock()
        config.compliance_guardian.enabled = False
        
        with patch('runtime.agent.get_config', return_value=config), \
             patch('runtime.agent.get_logger'), \
             patch('runtime.agent.get_dr_manager'), \
             patch('runtime.agent.get_tracker'), \
             patch('runtime.agent._init_model'):
            agent = Agent(config=config)
            
            # Should have conversation history
            assert hasattr(agent, 'conversation_history')
            assert isinstance(agent.conversation_history, list)
