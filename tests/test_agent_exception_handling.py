"""
Tests for exception handling in Agent
"""

import sys
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.agent import Agent


def test_agent_logs_conversation_start_exception(capsys):
    """Test that conversation.start exceptions are logged"""
    agent = Agent()

    # Mock the logger to raise an exception
    agent.logger = Mock()
    agent.logger.log_event.side_effect = Exception("Test exception")

    # Mock the model to avoid actual initialization
    agent.model = Mock()
    agent.model.generate.return_value = Mock(
        text="Test response", prompt_tokens=10, tokens_generated=20, total_tokens=30
    )

    # Call chat which should trigger the exception
    try:
        agent.chat("test message", "test-conv-id")
    except Exception:
        pass  # We expect some failures due to mocking

    # Check that the exception was logged to stdout
    captured = capsys.readouterr()
    assert "⚠ Failed to log conversation.start event: Test exception" in captured.out


def test_agent_logs_tool_call_exception(capsys):
    """Test that log_tool_call exceptions are logged"""
    agent = Agent()

    # Mock the logger to raise an exception for log_tool_call
    agent.logger = Mock()
    agent.logger.log_tool_call.side_effect = Exception("Tool call logging failed")
    agent.logger.log_event.return_value = None  # Don't fail on other events

    # Mock the model
    agent.model = Mock()
    # First call returns a tool call, second call returns final response
    agent.model.generate.side_effect = [
        Mock(
            text='<tool_call>{"tool": "math_calculator", "arguments": {"expression": "2+2"}}</tool_call>',
            prompt_tokens=10,
            tokens_generated=20,
            total_tokens=30,
        ),
        Mock(text="Final response", prompt_tokens=10, tokens_generated=20, total_tokens=30),
    ]

    # Mock the tool registry to have a calculator
    from tools.base import ToolResult, ToolStatus

    mock_tool = Mock()
    mock_tool.execute.return_value = ToolResult(status=ToolStatus.SUCCESS, output="4", error=None)
    agent.tool_registry.get = Mock(return_value=mock_tool)

    try:
        agent.chat("Calculate 2+2", "test-conv-id")
    except Exception:
        pass  # We expect some failures due to mocking

    # Check that the exception was logged to stdout
    captured = capsys.readouterr()
    assert (
        "⚠ Failed to log tool call for 'math_calculator': Tool call logging failed" in captured.out
    )


def test_agent_logs_track_tool_execution_exception(capsys):
    """Test that track_tool_execution exceptions are logged"""
    agent = Agent()

    # Mock the tracker to raise an exception
    agent.tracker = Mock()
    agent.tracker.track_tool_execution.side_effect = Exception("Tracker failed")

    # Mock the logger to not fail
    agent.logger = Mock()

    # Mock the model
    agent.model = Mock()
    agent.model.generate.side_effect = [
        Mock(
            text='<tool_call>{"tool": "math_calculator", "arguments": {"expression": "2+2"}}</tool_call>',
            prompt_tokens=10,
            tokens_generated=20,
            total_tokens=30,
        ),
        Mock(text="Final response", prompt_tokens=10, tokens_generated=20, total_tokens=30),
    ]

    # Mock the tool
    from tools.base import ToolResult, ToolStatus

    mock_tool = Mock()
    mock_tool.execute.return_value = ToolResult(status=ToolStatus.SUCCESS, output="4", error=None)
    agent.tool_registry.get = Mock(return_value=mock_tool)

    try:
        agent.chat("Calculate 2+2", "test-conv-id")
    except Exception:
        pass  # We expect some failures due to mocking

    # Check that the exception was logged to stdout
    captured = capsys.readouterr()
    assert "⚠ Failed to track tool execution for 'math_calculator': Tracker failed" in captured.out


def test_agent_logs_generation_exception(capsys):
    """Test that log_generation exceptions are logged"""
    agent = Agent()

    # Mock the logger to raise an exception for log_generation
    agent.logger = Mock()
    agent.logger.log_generation.side_effect = Exception("Generation logging failed")
    agent.logger.log_event.return_value = None  # Don't fail on events

    # Mock the model
    agent.model = Mock()
    agent.model.generate.return_value = Mock(
        text="Test response", prompt_tokens=10, tokens_generated=20, total_tokens=30
    )

    try:
        agent.chat("test message", "test-conv-id")
    except Exception:
        pass  # We expect some failures due to mocking

    # Check that the exception was logged to stdout
    captured = capsys.readouterr()
    assert "⚠ Failed to log generation: Generation logging failed" in captured.out


def test_agent_logs_conversation_end_exception(capsys):
    """Test that conversation.end exceptions are logged"""
    agent = Agent()

    # Mock the logger to raise exception only for conversation.end
    agent.logger = Mock()

    def log_event_side_effect(*args, **kwargs):
        if "event" in kwargs and kwargs["event"] == "conversation.end":
            raise Exception("End logging failed")
        return None

    agent.logger.log_event.side_effect = log_event_side_effect

    # Mock the model
    agent.model = Mock()
    agent.model.generate.return_value = Mock(
        text="Test response", prompt_tokens=10, tokens_generated=20, total_tokens=30
    )

    try:
        agent.chat("test message", "test-conv-id")
    except Exception:
        pass  # We expect some failures due to mocking

    # Check that the exception was logged to stdout
    captured = capsys.readouterr()
    assert "⚠ Failed to log conversation.end event: End logging failed" in captured.out
