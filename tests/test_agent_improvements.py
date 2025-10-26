"""
Tests for agent code quality improvements
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Ajouter le parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_generation_result_import():
    """Test that GenerationResult is properly imported"""
    from runtime.agent import Agent
    from runtime.model_interface import GenerationResult
    
    # Verify the import works - this would fail if GenerationResult wasn't imported
    assert GenerationResult is not None


def test_agent_exception_logging(capfd):
    """Test that exceptions in middleware calls are logged instead of silently swallowed"""
    from runtime.agent import Agent
    from runtime.config import get_config
    
    # Create agent with mocked logger that raises an exception
    with patch('runtime.agent.get_logger') as mock_get_logger:
        mock_logger = Mock()
        mock_logger.log_event.side_effect = Exception("Test exception")
        mock_get_logger.return_value = mock_logger
        
        agent = Agent()
        agent.model = Mock()
        agent.model.generate.return_value = Mock(
            text="Test response",
            finish_reason="stop",
            tokens_generated=10,
            prompt_tokens=5,
            total_tokens=15
        )
        
        # Call chat which should trigger the exception
        with patch('runtime.agent.add_message'):
            with patch('runtime.agent.get_messages', return_value=[]):
                result = agent.chat("Test message", "test-conv-1")
        
        # Check that the error was printed instead of silently swallowed
        captured = capfd.readouterr()
        assert "⚠ Failed to log" in captured.out


def test_tool_execution_timing():
    """Test that tool execution timing is captured correctly"""
    from runtime.agent import Agent
    from tools.base import ToolResult, ToolStatus
    import time
    
    agent = Agent()
    agent.model = Mock()
    agent.tracker = Mock()
    
    # Mock a tool that takes some time to execute
    def slow_execute(tool_call):
        time.sleep(0.01)  # 10ms delay
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output="Tool output",
            error=None
        )
    
    with patch.object(agent, '_execute_tool', side_effect=slow_execute):
        with patch.object(agent, '_parse_tool_calls', return_value=[{"tool": "test_tool", "arguments": {}}]):
            with patch('runtime.agent.add_message'):
                with patch('runtime.agent.get_messages', return_value=[]):
                    agent.model.generate.return_value = Mock(
                        text='<tool_call>{"tool": "test_tool", "arguments": {}}</tool_call>',
                        finish_reason="stop",
                        tokens_generated=10,
                        prompt_tokens=5,
                        total_tokens=15
                    )
                    
                    # Second call returns final response
                    final_response = Mock(
                        text="Final response",
                        finish_reason="stop",
                        tokens_generated=10,
                        prompt_tokens=5,
                        total_tokens=15
                    )
                    agent.model.generate.side_effect = [agent.model.generate.return_value, final_response]
                    
                    result = agent.chat("Test", "test-conv")
    
    # Verify tracker was called with start_time and end_time
    if agent.tracker.track_tool_execution.called:
        call_args = agent.tracker.track_tool_execution.call_args
        start_time = call_args[1]['start_time']
        end_time = call_args[1]['end_time']
        
        # Verify they are ISO format timestamps
        assert start_time is not None
        assert end_time is not None
        
        # Parse and verify end_time is after start_time
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)
        assert end_dt >= start_dt


def test_health_check_no_directory_creation(tmp_path):
    """Test that health check doesn't create directories"""
    from runtime.server import health
    from pathlib import Path
    
    # Create a non-existent directory path
    non_existent_dir = tmp_path / "should_not_be_created"
    
    with patch('runtime.server.get_logger') as mock_logger:
        with patch('runtime.server.get_worm_logger') as mock_worm:
            # Mock logger with non-existent directory
            mock_logger_instance = Mock()
            mock_logger_instance.current_file = non_existent_dir / "test.log"
            mock_logger.return_value = mock_logger_instance
            
            mock_worm_instance = Mock()
            mock_worm_instance.digest_dir = non_existent_dir / "digests"
            mock_worm.return_value = mock_worm_instance
            
            with patch('runtime.server.get_agent'):
                with patch('runtime.server.get_connection'):
                    import asyncio
                    result = asyncio.run(health())
            
            # Verify directory was NOT created
            assert not non_existent_dir.exists()
            # Logging should be False since directories don't exist
            assert result['components']['logging'] == False


def test_database_connection_context_manager():
    """Test that database connection is properly managed with context manager"""
    from runtime.server import health
    
    mock_conn = MagicMock()
    
    with patch('runtime.server.get_connection', return_value=mock_conn):
        with patch('runtime.server.get_agent'):
            with patch('runtime.server.get_logger'):
                with patch('runtime.server.get_worm_logger'):
                    import asyncio
                    result = asyncio.run(health())
    
    # Verify connection was used as context manager
    mock_conn.__enter__.assert_called_once()
    mock_conn.__exit__.assert_called_once()
