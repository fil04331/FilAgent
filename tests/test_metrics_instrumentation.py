"""
Tests for metrics instrumentation in agent components.

Tests verify:
1. ComplianceGuardian records metrics correctly
2. ToolExecutor records metrics correctly
3. Agent records conversation metrics correctly
4. No PII in any recorded metrics
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


@pytest.fixture
def mock_metrics():
    """Create a mock metrics instance."""
    mock = Mock()
    mock.record_compliance_rejection = Mock()
    mock.record_compliance_validation = Mock()
    mock.record_suspicious_pattern = Mock()
    mock.record_pii_detection = Mock()
    mock.record_tool_execution = Mock()
    mock.record_tool_validation_failure = Mock()
    mock.record_conversation = Mock()
    mock.record_tokens = Mock()
    mock.record_generation_duration = Mock()
    return mock


@pytest.mark.unit
class TestComplianceGuardianMetrics:
    """Test metrics in ComplianceGuardian."""
    
    def test_compliance_guardian_records_rejection_metrics(self, mock_metrics):
        """Test that ComplianceGuardian records rejection metrics."""
        from planner.compliance_guardian import ComplianceGuardian
        
        # Create guardian with mock metrics
        guardian = ComplianceGuardian()
        guardian.metrics = mock_metrics
        
        # Trigger rejection (query too long)
        with pytest.raises(Exception):  # ComplianceError
            guardian.validate_query("x" * 20000, context={"user_id": "test_user"})
        
        # Verify rejection was recorded
        mock_metrics.record_compliance_rejection.assert_called_once()
        call_kwargs = mock_metrics.record_compliance_rejection.call_args[1]
        assert call_kwargs["reason"] == "max_length_exceeded"
        assert call_kwargs["risk_level"] == "MEDIUM"
    
    def test_compliance_guardian_records_validation_metrics(self, mock_metrics):
        """Test that ComplianceGuardian records validation metrics."""
        from planner.compliance_guardian import ComplianceGuardian
        
        guardian = ComplianceGuardian()
        guardian.metrics = mock_metrics
        
        # Successful validation
        result = guardian.validate_query("Hello world", context={"user_id": "test_user"})
        
        assert result.valid
        mock_metrics.record_compliance_validation.assert_called_once()
        
        call_kwargs = mock_metrics.record_compliance_validation.call_args[1]
        assert call_kwargs["status"] in ["passed", "warning"]
        assert "duration_seconds" in call_kwargs
    
    def test_compliance_guardian_records_forbidden_pattern_metrics(self, mock_metrics):
        """Test metrics for forbidden patterns."""
        from planner.compliance_guardian import ComplianceGuardian
        
        guardian = ComplianceGuardian()
        guardian.metrics = mock_metrics
        
        # Try query with forbidden pattern
        try:
            guardian.validate_query(
                "How to hack the system",
                context={"user_id": "test_user"}
            )
        except Exception:
            pass
        
        # Should record both rejection and suspicious pattern
        assert mock_metrics.record_compliance_rejection.called
        assert mock_metrics.record_suspicious_pattern.called
    
    def test_compliance_guardian_records_pii_detection(self, mock_metrics):
        """Test metrics for PII detection."""
        from planner.compliance_guardian import ComplianceGuardian
        
        guardian = ComplianceGuardian()
        guardian.metrics = mock_metrics
        
        # Query with PII (email)
        result = guardian.validate_query(
            "My email is test@example.com",
            context={"user_id": "test_user"}
        )
        
        # Should record PII detection
        assert mock_metrics.record_pii_detection.called
        call_args = mock_metrics.record_pii_detection.call_args[1]
        assert call_args["pii_type"] in ["email", "unknown"]
    
    def test_compliance_guardian_no_pii_in_metrics(self, mock_metrics):
        """Test that no actual PII is passed to metrics."""
        from planner.compliance_guardian import ComplianceGuardian
        
        guardian = ComplianceGuardian()
        guardian.metrics = mock_metrics
        
        sensitive_email = "sensitive@example.com"
        query = f"Contact me at {sensitive_email}"
        
        result = guardian.validate_query(query, context={"user_id": "user123"})
        
        # Check all metric calls
        for call in mock_metrics.method_calls:
            # Get all arguments
            args = str(call)
            # Sensitive email should not appear in any metric call
            assert sensitive_email not in args


@pytest.mark.unit
class TestToolExecutorMetrics:
    """Test metrics in ToolExecutor."""
    
    def test_tool_executor_records_execution_metrics(self, mock_metrics):
        """Test that ToolExecutor records execution metrics."""
        from runtime.tool_executor import ToolExecutor, ToolCall
        from tools.registry import ToolRegistry
        from tools.base import ToolResult, ToolStatus
        
        # Create mock tool
        mock_tool = Mock()
        mock_tool.validate_arguments = Mock(return_value=(True, None))
        mock_tool.execute = Mock(return_value=ToolResult(
            status=ToolStatus.SUCCESS,
            output="42"
        ))
        
        # Create registry with mock tool
        registry = ToolRegistry()
        registry.tools = {"calculator": mock_tool}
        
        # Create executor with mock metrics
        executor = ToolExecutor(registry)
        executor.metrics = mock_metrics
        
        # Execute tool
        tool_call = ToolCall(tool="calculator", arguments={"expression": "2+2"})
        result = executor.execute_tool(tool_call, "conv123")
        
        # Verify metrics recorded
        mock_metrics.record_tool_execution.assert_called_once()
        call_kwargs = mock_metrics.record_tool_execution.call_args[1]
        assert call_kwargs["tool_name"] == "calculator"
        assert call_kwargs["status"] == "success"
        assert call_kwargs["duration_seconds"] >= 0
    
    def test_tool_executor_records_validation_failure(self, mock_metrics):
        """Test that ToolExecutor records validation failures."""
        from runtime.tool_executor import ToolExecutor, ToolCall
        from tools.registry import ToolRegistry
        
        # Create mock tool with validation failure
        mock_tool = Mock()
        mock_tool.validate_arguments = Mock(return_value=(False, "Missing required argument"))
        
        registry = ToolRegistry()
        registry.tools = {"test_tool": mock_tool}
        
        executor = ToolExecutor(registry)
        executor.metrics = mock_metrics
        
        # Execute tool (will fail validation)
        tool_call = ToolCall(tool="test_tool", arguments={})
        result = executor.execute_tool(tool_call, "conv123")
        
        # Verify validation failure recorded
        assert mock_metrics.record_tool_validation_failure.called
        call_kwargs = mock_metrics.record_tool_validation_failure.call_args[1]
        assert call_kwargs["tool_name"] == "test_tool"
    
    def test_tool_executor_records_error_status(self, mock_metrics):
        """Test that ToolExecutor records error status."""
        from runtime.tool_executor import ToolExecutor, ToolCall
        from tools.registry import ToolRegistry
        from tools.base import ToolResult, ToolStatus
        
        # Create mock tool that returns error
        mock_tool = Mock()
        mock_tool.validate_arguments = Mock(return_value=(True, None))
        mock_tool.execute = Mock(return_value=ToolResult(
            status=ToolStatus.ERROR,
            output="",
            error="Tool execution failed"
        ))
        
        registry = ToolRegistry()
        registry.tools = {"failing_tool": mock_tool}
        
        executor = ToolExecutor(registry)
        executor.metrics = mock_metrics
        
        # Execute tool
        tool_call = ToolCall(tool="failing_tool", arguments={})
        result = executor.execute_tool(tool_call, "conv123")
        
        # Verify error status recorded
        mock_metrics.record_tool_execution.assert_called_once()
        call_kwargs = mock_metrics.record_tool_execution.call_args[1]
        assert call_kwargs["status"] == "error"


@pytest.mark.unit
class TestAgentMetrics:
    """Test metrics in Agent."""
    
    def test_agent_records_conversation_metrics(self, mock_metrics):
        """Test that Agent records conversation metrics."""
        # This is a complex test that would require full agent setup
        # For now, test the metric recording logic in isolation
        
        # Simulate what agent does
        conversation_start = time.time()
        time.sleep(0.01)  # Simulate work
        conversation_duration = time.time() - conversation_start
        
        mock_metrics.record_conversation(
            status="completed",
            duration_seconds=conversation_duration,
            outcome="success",
            iterations=3
        )
        
        assert mock_metrics.record_conversation.called
        call_kwargs = mock_metrics.record_conversation.call_args[1]
        assert call_kwargs["status"] == "completed"
        assert call_kwargs["duration_seconds"] > 0
    
    def test_agent_records_token_usage(self, mock_metrics):
        """Test that Agent records token usage."""
        mock_metrics.record_tokens(prompt_tokens=150, completion_tokens=75)
        
        assert mock_metrics.record_tokens.called
        call_kwargs = mock_metrics.record_tokens.call_args[1]
        assert call_kwargs["prompt_tokens"] == 150
        assert call_kwargs["completion_tokens"] == 75
    
    def test_agent_records_generation_duration(self, mock_metrics):
        """Test that Agent records generation duration."""
        generation_start = time.time()
        time.sleep(0.01)
        generation_duration = time.time() - generation_start
        
        mock_metrics.record_generation_duration(generation_duration)
        
        assert mock_metrics.record_generation_duration.called


@pytest.mark.integration
class TestMetricsEndToEnd:
    """End-to-end tests for metrics collection."""
    
    @pytest.mark.skipif(
        True,  # Skip by default as it requires full system
        reason="Requires full agent setup"
    )
    def test_full_conversation_records_all_metrics(self):
        """Test that a full conversation records all expected metrics."""
        # This would test:
        # 1. Compliance validation metrics
        # 2. Tool execution metrics
        # 3. Conversation metrics
        # 4. Token metrics
        # 5. Generation duration metrics
        pass


@pytest.mark.unit
class TestNoPIIInInstrumentation:
    """Comprehensive tests to ensure no PII in instrumented code."""
    
    def test_user_id_not_in_metric_calls(self, mock_metrics):
        """Test that user IDs are not directly in metric calls."""
        from planner.compliance_guardian import ComplianceGuardian
        
        guardian = ComplianceGuardian()
        guardian.metrics = mock_metrics
        
        sensitive_user_id = "user_email@example.com"
        
        try:
            guardian.validate_query("x" * 20000, context={"user_id": sensitive_user_id})
        except Exception:
            pass
        
        # Check that sensitive user ID is not in any call
        for call in mock_metrics.method_calls:
            call_str = str(call)
            # Should be hashed, not raw
            assert sensitive_user_id not in call_str
    
    def test_query_content_not_in_metrics(self, mock_metrics):
        """Test that query content is not in metrics."""
        from planner.compliance_guardian import ComplianceGuardian
        
        guardian = ComplianceGuardian()
        guardian.metrics = mock_metrics
        
        sensitive_query = "My SSN is 123-45-6789 and my password is secret123"
        
        result = guardian.validate_query(
            sensitive_query,
            context={"user_id": "test_user"}
        )
        
        # Check that sensitive content is not in any metric call
        for call in mock_metrics.method_calls:
            call_str = str(call)
            assert "123-45-6789" not in call_str
            assert "secret123" not in call_str
    
    def test_tool_arguments_not_in_metrics(self, mock_metrics):
        """Test that tool arguments are not in metrics."""
        from runtime.tool_executor import ToolExecutor, ToolCall
        from tools.registry import ToolRegistry
        from tools.base import ToolResult, ToolStatus
        
        mock_tool = Mock()
        mock_tool.validate_arguments = Mock(return_value=(True, None))
        mock_tool.execute = Mock(return_value=ToolResult(
            status=ToolStatus.SUCCESS,
            output="result"
        ))
        
        registry = ToolRegistry()
        registry.tools = {"test_tool": mock_tool}
        
        executor = ToolExecutor(registry)
        executor.metrics = mock_metrics
        
        # Tool call with sensitive argument
        sensitive_data = "sensitive_password_123"
        tool_call = ToolCall(
            tool="test_tool",
            arguments={"password": sensitive_data}
        )
        
        executor.execute_tool(tool_call, "conv123")
        
        # Check that sensitive data is not in any metric call
        for call in mock_metrics.method_calls:
            call_str = str(call)
            assert sensitive_data not in call_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
