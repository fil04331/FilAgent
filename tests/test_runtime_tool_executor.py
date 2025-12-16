"""
Unit tests for runtime.tool_executor module

Tests the ToolExecutor component with Pydantic V2 validation.
"""

import pytest
from unittest.mock import Mock, MagicMock
from tools.base import ToolStatus, ToolResult
from tools.registry import ToolRegistry
from runtime.tool_executor import ToolExecutor, ToolCall, ToolExecutionResult


@pytest.mark.unit
class TestToolCall:
    """Test ToolCall Pydantic model"""
    
    def test_tool_call_creation(self):
        """Test creating a valid ToolCall"""
        tc = ToolCall(tool="calculator", arguments={"expression": "2+2"})
        
        assert tc.tool == "calculator"
        assert tc.arguments == {"expression": "2+2"}
    
    def test_tool_call_defaults(self):
        """Test ToolCall with default arguments"""
        tc = ToolCall(tool="test_tool")
        
        assert tc.tool == "test_tool"
        assert tc.arguments == {}
    
    def test_tool_call_validation(self):
        """Test Pydantic validation"""
        # Valid
        tc = ToolCall(tool="name", arguments={"key": "value"})
        assert tc.tool == "name"
        
        # Missing required field
        with pytest.raises(Exception):  # Pydantic ValidationError
            ToolCall(arguments={"key": "value"})  # Missing 'tool'


@pytest.mark.unit
class TestToolExecutionResult:
    """Test ToolExecutionResult Pydantic model"""
    
    def test_execution_result_creation(self):
        """Test creating execution result"""
        result = ToolExecutionResult(
            tool_name="calculator",
            status=ToolStatus.SUCCESS,
            output="4",
            error=None,
            start_time="2024-01-01T00:00:00",
            end_time="2024-01-01T00:00:01",
            duration_ms=1000.0,
            input_hash="abc123",
            output_hash="def456",
        )
        
        assert result.tool_name == "calculator"
        assert result.status == ToolStatus.SUCCESS
        assert result.output == "4"
        assert result.duration_ms == 1000.0


@pytest.mark.unit
class TestToolExecutor:
    """Test ToolExecutor component"""
    
    @pytest.fixture
    def mock_tool(self):
        """Create a mock tool"""
        tool = Mock()
        tool.validate_arguments.return_value = (True, None)
        tool.execute.return_value = ToolResult(
            status=ToolStatus.SUCCESS,
            output="Result",
            error=None,
        )
        return tool
    
    @pytest.fixture
    def mock_registry(self, mock_tool):
        """Create a mock registry with a tool"""
        registry = Mock(spec=ToolRegistry)
        registry.get.return_value = mock_tool
        return registry
    
    @pytest.fixture
    def executor(self, mock_registry):
        """Create a ToolExecutor with mock dependencies"""
        return ToolExecutor(
            tool_registry=mock_registry,
            logger=None,
            tracker=None,
        )
    
    def test_executor_initialization(self, mock_registry):
        """Test executor initializes correctly"""
        executor = ToolExecutor(
            tool_registry=mock_registry,
            logger=None,
            tracker=None,
        )
        
        assert executor.tool_registry == mock_registry
        assert executor.logger is None
        assert executor.tracker is None
    
    def test_validate_tool_call_success(self, executor, mock_registry, mock_tool):
        """Test successful tool call validation"""
        tc = ToolCall(tool="calculator", arguments={"expression": "2+2"})
        
        is_valid, error = executor.validate_tool_call(tc)
        
        assert is_valid is True
        assert error is None
        mock_registry.get.assert_called_once_with("calculator")
        mock_tool.validate_arguments.assert_called_once_with({"expression": "2+2"})
    
    def test_validate_tool_call_not_found(self, executor, mock_registry):
        """Test validation when tool not in registry"""
        mock_registry.get.return_value = None
        
        tc = ToolCall(tool="nonexistent", arguments={})
        is_valid, error = executor.validate_tool_call(tc)
        
        assert is_valid is False
        assert "not found" in error.lower()
    
    def test_validate_tool_call_invalid_args(self, executor, mock_registry, mock_tool):
        """Test validation with invalid arguments"""
        mock_tool.validate_arguments.return_value = (False, "Invalid expression")
        
        tc = ToolCall(tool="calculator", arguments={"bad": "args"})
        is_valid, error = executor.validate_tool_call(tc)
        
        assert is_valid is False
        assert "Invalid expression" in error
    
    def test_execute_tool_success(self, executor, mock_tool):
        """Test successful tool execution"""
        tc = ToolCall(tool="calculator", arguments={"expression": "2+2"})
        
        result = executor.execute_tool(tc, "conv123", "task456")
        
        assert result.tool_name == "calculator"
        assert result.status == ToolStatus.SUCCESS
        assert result.output == "Result"
        assert result.error is None
        assert result.duration_ms >= 0
        assert len(result.input_hash) == 64  # SHA256 hex length
        assert len(result.output_hash) == 64
    
    def test_execute_tool_validation_failure(self, executor, mock_registry):
        """Test execution with validation failure"""
        mock_registry.get.return_value = None
        
        tc = ToolCall(tool="nonexistent", arguments={})
        result = executor.execute_tool(tc, "conv123")
        
        assert result.status == ToolStatus.ERROR
        assert "not found" in result.error.lower()
        assert result.output == ""
    
    def test_execute_tool_with_logger(self, mock_registry, mock_tool):
        """Test execution logs to logger"""
        mock_logger = Mock()
        executor = ToolExecutor(
            tool_registry=mock_registry,
            logger=mock_logger,
            tracker=None,
        )
        
        tc = ToolCall(tool="calculator", arguments={"expression": "2+2"})
        result = executor.execute_tool(tc, "conv123", "task456")
        
        # Verify logger was called
        mock_logger.log_tool_call.assert_called_once()
        call_args = mock_logger.log_tool_call.call_args
        assert call_args[1]["tool_name"] == "calculator"
        assert call_args[1]["conversation_id"] == "conv123"
        assert call_args[1]["task_id"] == "task456"
    
    def test_execute_tool_with_tracker(self, mock_registry, mock_tool):
        """Test execution tracks provenance"""
        mock_tracker = Mock()
        executor = ToolExecutor(
            tool_registry=mock_registry,
            logger=None,
            tracker=mock_tracker,
        )
        
        tc = ToolCall(tool="calculator", arguments={"expression": "2+2"})
        result = executor.execute_tool(tc, "conv123", "task456")
        
        # Verify tracker was called
        mock_tracker.track_tool_execution.assert_called_once()
        call_args = mock_tracker.track_tool_execution.call_args
        assert call_args[1]["tool_name"] == "calculator"
        assert call_args[1]["task_id"] == "task456"
    
    def test_execute_batch_success(self, executor):
        """Test batch execution of multiple tool calls"""
        tool_calls = [
            ToolCall(tool="tool1", arguments={"a": 1}),
            ToolCall(tool="tool2", arguments={"b": 2}),
            ToolCall(tool="tool3", arguments={"c": 3}),
        ]
        
        results = executor.execute_batch(tool_calls, "conv123", "task456")
        
        assert len(results) == 3
        assert all(isinstance(r, ToolExecutionResult) for r in results)
        assert all(r.status == ToolStatus.SUCCESS for r in results)
    
    def test_execute_batch_empty(self, executor):
        """Test batch execution with empty list"""
        results = executor.execute_batch([], "conv123")
        
        assert results == []
    
    def test_format_results_success(self, executor):
        """Test formatting successful results"""
        results = [
            ToolExecutionResult(
                tool_name="tool1",
                status=ToolStatus.SUCCESS,
                output="Output 1",
                error=None,
                start_time="",
                end_time="",
                duration_ms=0,
                input_hash="",
                output_hash="",
            ),
            ToolExecutionResult(
                tool_name="tool2",
                status=ToolStatus.SUCCESS,
                output="Output 2",
                error=None,
                start_time="",
                end_time="",
                duration_ms=0,
                input_hash="",
                output_hash="",
            ),
        ]
        
        formatted = executor.format_results(results)
        
        assert "Outil 1" in formatted
        assert "tool1" in formatted
        assert "SUCCESS" in formatted
        assert "Output 1" in formatted
        assert "Outil 2" in formatted
        assert "Output 2" in formatted
    
    def test_format_results_with_errors(self, executor):
        """Test formatting results with errors"""
        results = [
            ToolExecutionResult(
                tool_name="tool1",
                status=ToolStatus.SUCCESS,
                output="Success",
                error=None,
                start_time="",
                end_time="",
                duration_ms=0,
                input_hash="",
                output_hash="",
            ),
            ToolExecutionResult(
                tool_name="tool2",
                status=ToolStatus.ERROR,
                output="",
                error="Error message",
                start_time="",
                end_time="",
                duration_ms=0,
                input_hash="",
                output_hash="",
            ),
        ]
        
        formatted = executor.format_results(results)
        
        assert "SUCCESS" in formatted
        assert "ERROR" in formatted
        assert "Error message" in formatted
    
    def test_format_results_empty(self, executor):
        """Test formatting empty results"""
        formatted = executor.format_results([])
        
        assert formatted == ""
    
    def test_execute_tool_error_handling(self, executor, mock_registry, mock_tool):
        """Test execution handles tool errors gracefully"""
        mock_tool.execute.return_value = ToolResult(
            status=ToolStatus.ERROR,
            output="",
            error="Tool execution failed",
        )
        
        tc = ToolCall(tool="calculator", arguments={})
        result = executor.execute_tool(tc, "conv123")
        
        assert result.status == ToolStatus.ERROR
        assert result.error == "Tool execution failed"
    
    def test_logger_exception_handling(self, mock_registry, mock_tool):
        """Test execution continues even if logger fails"""
        mock_logger = Mock()
        mock_logger.log_tool_call.side_effect = Exception("Logger failed")
        
        executor = ToolExecutor(
            tool_registry=mock_registry,
            logger=mock_logger,
            tracker=None,
        )
        
        tc = ToolCall(tool="calculator", arguments={})
        # Should not raise exception
        result = executor.execute_tool(tc, "conv123")
        
        assert result.status == ToolStatus.SUCCESS
    
    def test_tracker_exception_handling(self, mock_registry, mock_tool):
        """Test execution continues even if tracker fails"""
        mock_tracker = Mock()
        mock_tracker.track_tool_execution.side_effect = Exception("Tracker failed")
        
        executor = ToolExecutor(
            tool_registry=mock_registry,
            logger=None,
            tracker=mock_tracker,
        )
        
        tc = ToolCall(tool="calculator", arguments={})
        # Should not raise exception
        result = executor.execute_tool(tc, "conv123")
        
        assert result.status == ToolStatus.SUCCESS
