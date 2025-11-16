"""
Comprehensive tests for tools/base.py

Tests cover:
1. Abstract class contract tests - Ensure BaseTool cannot be instantiated directly
2. Validation error paths - Test all validation error scenarios
3. Status handling - Test all ToolStatus values and ToolResult behavior
"""
import pytest
import sys
from pathlib import Path
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.base import BaseTool, ToolResult, ToolStatus


# ============================================================================
# Test Fixtures: Mock Tool Implementations
# ============================================================================


class ConcreteToolGood(BaseTool):
    """Concrete implementation of BaseTool for testing"""

    def __init__(self):
        super().__init__(
            name="test_tool",
            description="A test tool for unit testing"
        )

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute the tool"""
        is_valid, error = self.validate_arguments(arguments)
        if not is_valid:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=error
            )

        operation = arguments.get("operation", "default")

        if operation == "success":
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output="Operation completed successfully",
                metadata={"operation": operation}
            )
        elif operation == "error":
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error="Simulated error"
            )
        elif operation == "timeout":
            return ToolResult(
                status=ToolStatus.TIMEOUT,
                output="",
                error="Operation timed out"
            )
        elif operation == "blocked":
            return ToolResult(
                status=ToolStatus.BLOCKED,
                output="",
                error="Operation blocked by policy"
            )
        else:
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=f"Executed with operation: {operation}"
            )

    def validate_arguments(self, arguments: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate arguments"""
        if not isinstance(arguments, dict):
            return False, "Arguments must be a dictionary"

        if "required_param" in arguments:
            if not isinstance(arguments["required_param"], str):
                return False, "required_param must be a string"

        return True, None

    def _get_parameters_schema(self) -> Dict[str, Any]:
        """Get parameters schema"""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "Operation to perform"
                },
                "required_param": {
                    "type": "string",
                    "description": "Required parameter"
                }
            }
        }


class IncompleteToolNoExecute(BaseTool):
    """Tool missing execute() implementation"""

    def __init__(self):
        super().__init__(name="incomplete", description="Incomplete tool")

    def validate_arguments(self, arguments: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        return True, None

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {}


class IncompleteToolNoValidate(BaseTool):
    """Tool missing validate_arguments() implementation"""

    def __init__(self):
        super().__init__(name="incomplete", description="Incomplete tool")

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        return ToolResult(status=ToolStatus.SUCCESS, output="test")

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {}


class IncompleteToolNoSchema(BaseTool):
    """Tool missing _get_parameters_schema() implementation"""

    def __init__(self):
        super().__init__(name="incomplete", description="Incomplete tool")

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        return ToolResult(status=ToolStatus.SUCCESS, output="test")

    def validate_arguments(self, arguments: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        return True, None


# ============================================================================
# 1. Abstract Class Contract Tests
# ============================================================================


@pytest.mark.unit
def test_cannot_instantiate_abstract_base_tool():
    """Test that BaseTool cannot be instantiated directly"""
    with pytest.raises(TypeError) as exc_info:
        BaseTool(name="test", description="test")

    # Verify error message mentions abstract methods
    error_msg = str(exc_info.value)
    assert "abstract" in error_msg.lower() or "Can't instantiate" in error_msg


@pytest.mark.unit
def test_concrete_tool_can_be_instantiated():
    """Test that a properly implemented concrete tool can be instantiated"""
    tool = ConcreteToolGood()
    assert tool is not None
    assert tool.name == "test_tool"
    assert tool.description == "A test tool for unit testing"


@pytest.mark.unit
def test_missing_execute_raises_type_error():
    """Test that missing execute() implementation raises TypeError"""
    with pytest.raises(TypeError) as exc_info:
        IncompleteToolNoExecute()

    error_msg = str(exc_info.value)
    assert "abstract" in error_msg.lower() or "execute" in error_msg.lower()


@pytest.mark.unit
def test_missing_validate_arguments_raises_type_error():
    """Test that missing validate_arguments() implementation raises TypeError"""
    with pytest.raises(TypeError) as exc_info:
        IncompleteToolNoValidate()

    error_msg = str(exc_info.value)
    assert "abstract" in error_msg.lower() or "validate_arguments" in error_msg.lower()


@pytest.mark.unit
def test_missing_get_parameters_schema_raises_type_error():
    """Test that missing _get_parameters_schema() implementation raises TypeError"""
    with pytest.raises(TypeError) as exc_info:
        IncompleteToolNoSchema()

    error_msg = str(exc_info.value)
    assert "abstract" in error_msg.lower() or "_get_parameters_schema" in error_msg.lower()


@pytest.mark.unit
def test_base_tool_has_name_and_description():
    """Test that BaseTool properly initializes name and description"""
    tool = ConcreteToolGood()
    assert hasattr(tool, 'name')
    assert hasattr(tool, 'description')
    assert tool.name == "test_tool"
    assert tool.description == "A test tool for unit testing"


@pytest.mark.unit
def test_get_schema_returns_correct_structure():
    """Test that get_schema() returns proper structure"""
    tool = ConcreteToolGood()
    schema = tool.get_schema()

    assert isinstance(schema, dict)
    assert "name" in schema
    assert "description" in schema
    assert "parameters" in schema
    assert schema["name"] == "test_tool"
    assert schema["description"] == "A test tool for unit testing"
    assert isinstance(schema["parameters"], dict)


# ============================================================================
# 2. Validation Error Paths
# ============================================================================


@pytest.mark.unit
def test_validate_arguments_with_valid_dict():
    """Test validation with valid dictionary arguments"""
    tool = ConcreteToolGood()
    is_valid, error = tool.validate_arguments({"operation": "test"})

    assert is_valid is True
    assert error is None


@pytest.mark.unit
def test_validate_arguments_with_invalid_type():
    """Test validation with non-dict arguments"""
    tool = ConcreteToolGood()
    is_valid, error = tool.validate_arguments("not a dict")

    assert is_valid is False
    assert error is not None
    assert "dictionary" in error.lower()


@pytest.mark.unit
def test_validate_arguments_with_wrong_param_type():
    """Test validation with wrong parameter type"""
    tool = ConcreteToolGood()
    is_valid, error = tool.validate_arguments({"required_param": 123})

    assert is_valid is False
    assert error is not None
    assert "string" in error.lower()


@pytest.mark.unit
def test_execute_with_invalid_arguments():
    """Test execute with invalid arguments returns ERROR status"""
    tool = ConcreteToolGood()
    result = tool.execute("not a dict")

    assert result.status == ToolStatus.ERROR
    assert result.error is not None
    assert "dictionary" in result.error.lower()


@pytest.mark.unit
def test_execute_with_validation_failure():
    """Test execute with validation failure"""
    tool = ConcreteToolGood()
    result = tool.execute({"required_param": 123})

    assert result.status == ToolStatus.ERROR
    assert result.error is not None
    assert "string" in result.error.lower()


# ============================================================================
# 3. Status Handling Tests
# ============================================================================


@pytest.mark.unit
def test_tool_status_enum_values():
    """Test all ToolStatus enum values exist"""
    assert hasattr(ToolStatus, 'SUCCESS')
    assert hasattr(ToolStatus, 'ERROR')
    assert hasattr(ToolStatus, 'TIMEOUT')
    assert hasattr(ToolStatus, 'BLOCKED')

    assert ToolStatus.SUCCESS.value == "success"
    assert ToolStatus.ERROR.value == "error"
    assert ToolStatus.TIMEOUT.value == "timeout"
    assert ToolStatus.BLOCKED.value == "blocked"


@pytest.mark.unit
def test_tool_result_success():
    """Test ToolResult with SUCCESS status"""
    result = ToolResult(
        status=ToolStatus.SUCCESS,
        output="Operation successful"
    )

    assert result.status == ToolStatus.SUCCESS
    assert result.output == "Operation successful"
    assert result.is_success() is True
    assert result.error is None


@pytest.mark.unit
def test_tool_result_error():
    """Test ToolResult with ERROR status"""
    result = ToolResult(
        status=ToolStatus.ERROR,
        output="",
        error="Something went wrong"
    )

    assert result.status == ToolStatus.ERROR
    assert result.is_success() is False
    assert result.error == "Something went wrong"


@pytest.mark.unit
def test_tool_result_timeout():
    """Test ToolResult with TIMEOUT status"""
    result = ToolResult(
        status=ToolStatus.TIMEOUT,
        output="",
        error="Operation timed out after 30s"
    )

    assert result.status == ToolStatus.TIMEOUT
    assert result.is_success() is False
    assert result.error == "Operation timed out after 30s"


@pytest.mark.unit
def test_tool_result_blocked():
    """Test ToolResult with BLOCKED status"""
    result = ToolResult(
        status=ToolStatus.BLOCKED,
        output="",
        error="Operation blocked by security policy"
    )

    assert result.status == ToolStatus.BLOCKED
    assert result.is_success() is False
    assert result.error == "Operation blocked by security policy"


@pytest.mark.unit
def test_tool_result_is_success_method():
    """Test is_success() method for all statuses"""
    success_result = ToolResult(status=ToolStatus.SUCCESS, output="ok")
    error_result = ToolResult(status=ToolStatus.ERROR, output="", error="err")
    timeout_result = ToolResult(status=ToolStatus.TIMEOUT, output="", error="timeout")
    blocked_result = ToolResult(status=ToolStatus.BLOCKED, output="", error="blocked")

    assert success_result.is_success() is True
    assert error_result.is_success() is False
    assert timeout_result.is_success() is False
    assert blocked_result.is_success() is False


@pytest.mark.unit
def test_tool_result_with_metadata():
    """Test ToolResult with metadata"""
    metadata = {
        "execution_time": 1.23,
        "resource_usage": {"cpu": 0.5, "memory": 1024}
    }

    result = ToolResult(
        status=ToolStatus.SUCCESS,
        output="Done",
        metadata=metadata
    )

    assert result.metadata is not None
    assert result.metadata["execution_time"] == 1.23
    assert result.metadata["resource_usage"]["cpu"] == 0.5


@pytest.mark.unit
def test_tool_result_error_message_alias():
    """Test error_message alias harmonization"""
    # Create with error_message (should populate error)
    result1 = ToolResult(
        status=ToolStatus.ERROR,
        output="",
        error_message="Test error"
    )

    assert result1.error == "Test error"
    assert result1.error_message == "Test error"

    # Create with error (should populate error_message)
    result2 = ToolResult(
        status=ToolStatus.ERROR,
        output="",
        error="Another error"
    )

    assert result2.error == "Another error"
    assert result2.error_message == "Another error"


@pytest.mark.unit
def test_tool_result_both_error_fields():
    """Test when both error and error_message are provided"""
    result = ToolResult(
        status=ToolStatus.ERROR,
        output="",
        error="Primary error",
        error_message="Secondary error"
    )

    # When both are provided, they remain unchanged
    # The __post_init__ only harmonizes when one is None
    assert result.error == "Primary error"
    assert result.error_message == "Secondary error"


# ============================================================================
# 4. Integration Tests with Concrete Tool
# ============================================================================


@pytest.mark.unit
def test_concrete_tool_success_operation():
    """Test concrete tool with success operation"""
    tool = ConcreteToolGood()
    result = tool.execute({"operation": "success"})

    assert result.is_success()
    assert result.status == ToolStatus.SUCCESS
    assert "successfully" in result.output.lower()
    assert result.metadata is not None
    assert result.metadata["operation"] == "success"


@pytest.mark.unit
def test_concrete_tool_error_operation():
    """Test concrete tool with error operation"""
    tool = ConcreteToolGood()
    result = tool.execute({"operation": "error"})

    assert not result.is_success()
    assert result.status == ToolStatus.ERROR
    assert result.error == "Simulated error"


@pytest.mark.unit
def test_concrete_tool_timeout_operation():
    """Test concrete tool with timeout operation"""
    tool = ConcreteToolGood()
    result = tool.execute({"operation": "timeout"})

    assert not result.is_success()
    assert result.status == ToolStatus.TIMEOUT
    assert "timed out" in result.error.lower()


@pytest.mark.unit
def test_concrete_tool_blocked_operation():
    """Test concrete tool with blocked operation"""
    tool = ConcreteToolGood()
    result = tool.execute({"operation": "blocked"})

    assert not result.is_success()
    assert result.status == ToolStatus.BLOCKED
    assert "blocked" in result.error.lower()


@pytest.mark.unit
def test_concrete_tool_default_operation():
    """Test concrete tool with default operation"""
    tool = ConcreteToolGood()
    result = tool.execute({"operation": "custom"})

    assert result.is_success()
    assert "custom" in result.output


@pytest.mark.unit
def test_concrete_tool_empty_arguments():
    """Test concrete tool with empty arguments dict"""
    tool = ConcreteToolGood()
    result = tool.execute({})

    assert result.is_success()  # Should work with empty dict


# ============================================================================
# 5. Edge Cases and Boundary Tests
# ============================================================================


@pytest.mark.unit
def test_tool_result_with_empty_output():
    """Test ToolResult with empty output string"""
    result = ToolResult(
        status=ToolStatus.SUCCESS,
        output=""
    )

    assert result.status == ToolStatus.SUCCESS
    assert result.output == ""
    assert result.is_success()


@pytest.mark.unit
def test_tool_result_with_none_metadata():
    """Test ToolResult with None metadata"""
    result = ToolResult(
        status=ToolStatus.SUCCESS,
        output="test",
        metadata=None
    )

    assert result.metadata is None


@pytest.mark.unit
def test_tool_result_with_empty_metadata():
    """Test ToolResult with empty metadata dict"""
    result = ToolResult(
        status=ToolStatus.SUCCESS,
        output="test",
        metadata={}
    )

    assert result.metadata == {}
    assert isinstance(result.metadata, dict)


@pytest.mark.unit
def test_validate_arguments_returns_tuple():
    """Test that validate_arguments always returns a tuple"""
    tool = ConcreteToolGood()

    # Valid case
    result = tool.validate_arguments({"operation": "test"})
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], bool)
    assert result[1] is None or isinstance(result[1], str)

    # Invalid case
    result = tool.validate_arguments("invalid")
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], bool)
    assert isinstance(result[1], str)


@pytest.mark.unit
def test_get_schema_includes_parameters():
    """Test that get_schema() includes parameters from _get_parameters_schema()"""
    tool = ConcreteToolGood()
    schema = tool.get_schema()

    assert "parameters" in schema
    params = schema["parameters"]
    assert "type" in params
    assert "properties" in params
    assert "operation" in params["properties"]
    assert "required_param" in params["properties"]


@pytest.mark.unit
def test_tool_status_enum_is_string():
    """Test that ToolStatus enum values are strings"""
    assert isinstance(ToolStatus.SUCCESS.value, str)
    assert isinstance(ToolStatus.ERROR.value, str)
    assert isinstance(ToolStatus.TIMEOUT.value, str)
    assert isinstance(ToolStatus.BLOCKED.value, str)


@pytest.mark.unit
def test_tool_status_comparison():
    """Test ToolStatus enum comparison"""
    result = ToolResult(status=ToolStatus.SUCCESS, output="test")

    assert result.status == ToolStatus.SUCCESS
    assert result.status != ToolStatus.ERROR
    assert result.status != ToolStatus.TIMEOUT
    assert result.status != ToolStatus.BLOCKED


@pytest.mark.unit
def test_tool_result_dataclass_fields():
    """Test that ToolResult has all expected dataclass fields"""
    result = ToolResult(
        status=ToolStatus.SUCCESS,
        output="test output",
        error="test error",
        metadata={"key": "value"},
        error_message="test error message"
    )

    assert hasattr(result, 'status')
    assert hasattr(result, 'output')
    assert hasattr(result, 'error')
    assert hasattr(result, 'metadata')
    assert hasattr(result, 'error_message')


@pytest.mark.unit
def test_multiple_tool_instances_are_independent():
    """Test that multiple tool instances are independent"""
    tool1 = ConcreteToolGood()
    tool2 = ConcreteToolGood()

    result1 = tool1.execute({"operation": "success"})
    result2 = tool2.execute({"operation": "error"})

    # Results should be independent
    assert result1.is_success()
    assert not result2.is_success()

    # Tools should be different instances
    assert tool1 is not tool2
