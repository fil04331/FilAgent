"""
Tool Executor Component - Validation and Execution

Handles tool validation and execution with Pydantic V2 schema validation.
This component is responsible for:
1. Validating tool call parameters against schemas
2. Executing tools safely
3. Handling errors and timeouts
4. Logging execution details

Key Principles:
1. Single Responsibility: ONLY tool execution
2. Strict Typing: Pydantic V2 for all inputs/outputs
3. No side effects: Logging via dependency injection
4. Testability: All dependencies injected
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import hashlib

from pydantic import BaseModel, Field

from tools.base import ToolStatus
from tools.registry import ToolRegistry

# Import metrics for observability
try:
    from runtime.metrics import get_agent_metrics

    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False

# Import OpenTelemetry for distributed tracing
try:
    from runtime.telemetry import get_tracer, get_trace_context

    TELEMETRY_AVAILABLE = True
except ImportError:
    TELEMETRY_AVAILABLE = False

    def get_tracer(name=None):
        from contextlib import contextmanager

        class NoOpTracer:
            @contextmanager
            def start_as_current_span(self, name, **kwargs):
                yield None

        return NoOpTracer()

    def get_trace_context():
        return {}


class ToolCall(BaseModel):
    """
    Structured tool call with Pydantic validation.

    This replaces the regex-based parsing with structured output.
    """

    tool: str = Field(description="Name of the tool to execute")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class ToolExecutionResult(BaseModel):
    """
    Result of tool execution with metadata.

    Extends ToolResult with execution metadata for tracking.
    """

    tool_name: str
    status: ToolStatus
    output: str
    error: Optional[str] = None
    start_time: str
    end_time: str
    duration_ms: float
    input_hash: str
    output_hash: str


class ToolExecutor:
    """
    Executes and validates tool calls.

    This component handles all tool execution logic that was previously
    embedded in the Agent class.

    Dependencies are injected to maintain testability and flexibility.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        logger: Optional[Any] = None,
        tracker: Optional[Any] = None,
    ):
        """
        Initialize tool executor with dependencies.

        Args:
            tool_registry: Registry of available tools
            logger: Optional logger for tool execution events
            tracker: Optional provenance tracker
        """
        self.tool_registry = tool_registry
        self.logger = logger
        self.tracker = tracker

        # Initialize metrics collector
        if METRICS_AVAILABLE:
            self.metrics = get_agent_metrics()
        else:
            self.metrics = None

        # Initialize OpenTelemetry tracer
        if TELEMETRY_AVAILABLE:
            self.tracer = get_tracer("filagent.tool_executor")
        else:
            self.tracer = get_tracer()  # No-op tracer

    def validate_tool_call(self, tool_call: ToolCall) -> tuple[bool, Optional[str]]:
        """
        Validate a tool call before execution.

        Args:
            tool_call: Structured tool call to validate

        Returns:
            (is_valid, error_message)
        """
        # Check if tool exists
        tool = self.tool_registry.get(tool_call.tool)
        if tool is None:
            return False, f"Tool '{tool_call.tool}' not found in registry"

        # Validate arguments using tool's validation method
        is_valid, error_msg = tool.validate_arguments(tool_call.arguments)
        if not is_valid:
            # Record validation failure metric
            if self.metrics:
                # Categorize error type from message
                error_type = "invalid_type"
                if "missing" in error_msg.lower():
                    error_type = "missing_argument"
                elif "type" in error_msg.lower():
                    error_type = "invalid_type"
                elif "value" in error_msg.lower():
                    error_type = "invalid_value"

                self.metrics.record_tool_validation_failure(
                    tool_name=tool_call.tool, error_type=error_type
                )

            return False, f"Invalid arguments for '{tool_call.tool}': {error_msg}"

        return True, None

    def execute_tool(
        self,
        tool_call: ToolCall,
        conversation_id: str,
        task_id: Optional[str] = None,
    ) -> ToolExecutionResult:
        """
        Execute a validated tool call with full tracking.

        Args:
            tool_call: Structured tool call to execute
            conversation_id: Conversation identifier
            task_id: Optional task identifier

        Returns:
            ToolExecutionResult with status and metadata
        """
        with self.tracer.start_as_current_span(
            f"tool.execute.{tool_call.tool}",
            attributes={
                "tool.name": tool_call.tool,
                "conversation_id": conversation_id,
                "task_id": task_id or "",
            },
        ) as span:
            start_time = datetime.now()
            start_time_iso = start_time.isoformat()

            # Validate before execution
            is_valid, error_msg = self.validate_tool_call(tool_call)
            if not is_valid:
                if span:
                    span.set_attribute("tool.validation.success", False)
                    span.set_attribute("tool.error", error_msg)
                end_time_iso = datetime.now().isoformat()

                # Record validation failure metric
                if self.metrics:
                    self.metrics.record_tool_execution(
                        tool_name=tool_call.tool, duration_seconds=0.0, status="validation_error"
                    )

                return ToolExecutionResult(
                    tool_name=tool_call.tool,
                    status=ToolStatus.ERROR,
                    output="",
                    error=error_msg,
                    start_time=start_time_iso,
                    end_time=end_time_iso,
                    duration_ms=0.0,
                    input_hash="",
                    output_hash="",
                )

            if span:
                span.set_attribute("tool.validation.success", True)

            # Get tool and execute
            tool = self.tool_registry.get(tool_call.tool)
            result = tool.execute(tool_call.arguments)

            if span:
                span.set_attribute("tool.execution.success", result.is_success())
                if not result.is_success() and result.error:
                    span.set_attribute("tool.error", result.error)

            # Calculate execution time
            end_time = datetime.now()
            end_time_iso = end_time.isoformat()
            duration_ms = (end_time - start_time).total_seconds() * 1000

            if span:
                span.set_attribute("tool.duration_ms", duration_ms)

            # Compute hashes for provenance
            input_hash = hashlib.sha256(str(tool_call.arguments).encode()).hexdigest()
            output_payload = result.output if result.is_success() else (result.error or "")
            output_hash = hashlib.sha256(str(output_payload).encode()).hexdigest()

            # Log execution if logger available with trace context
            if self.logger:
                try:
                    trace_ctx = get_trace_context()
                    self.logger.log_tool_call(
                        tool_name=tool_call.tool,
                        arguments=tool_call.arguments,
                        conversation_id=conversation_id,
                        task_id=task_id,
                        success=result.is_success(),
                        output=output_payload,
                        **trace_ctx,  # Add trace_id and span_id to logs
                    )
                except Exception as e:
                    print(f"⚠ Failed to log tool call for '{tool_call.tool}': {e}")

            # Track provenance if tracker available
            if self.tracker:
                try:
                    self.tracker.track_tool_execution(
                        tool_name=tool_call.tool,
                        tool_input_hash=input_hash,
                        tool_output_hash=output_hash,
                        task_id=task_id or conversation_id,
                        start_time=start_time_iso,
                        end_time=end_time_iso,
                    )
                except Exception as e:
                    print(f"⚠ Failed to track tool execution for '{tool_call.tool}': {e}")

            # Record execution metrics
            if self.metrics:
                status = "success" if result.is_success() else "error"
                self.metrics.record_tool_execution(
                    tool_name=tool_call.tool,
                    duration_seconds=duration_ms / 1000.0,  # Convert to seconds
                    status=status,
                )

            return ToolExecutionResult(
                tool_name=tool_call.tool,
                status=result.status,
                output=result.output,
                error=result.error,
                start_time=start_time_iso,
                end_time=end_time_iso,
                duration_ms=duration_ms,
                input_hash=input_hash,
                output_hash=output_hash,
            )

    def execute_batch(
        self,
        tool_calls: List[ToolCall],
        conversation_id: str,
        task_id: Optional[str] = None,
    ) -> List[ToolExecutionResult]:
        """
        Execute multiple tool calls in sequence.

        Args:
            tool_calls: List of tool calls to execute
            conversation_id: Conversation identifier
            task_id: Optional task identifier

        Returns:
            List of execution results
        """
        results = []
        for tool_call in tool_calls:
            result = self.execute_tool(tool_call, conversation_id, task_id)
            results.append(result)

        return results

    def format_results(self, results: List[ToolExecutionResult]) -> str:
        """
        Format tool execution results for context injection.

        Args:
            results: List of execution results

        Returns:
            Formatted string for LLM context
        """
        formatted = []
        for i, result in enumerate(results, 1):
            if result.status == ToolStatus.SUCCESS:
                formatted.append(f"Outil {i} ({result.tool_name}): SUCCESS\n{result.output}")
            else:
                formatted.append(f"Outil {i} ({result.tool_name}): ERROR\n{result.error}")

        return "\n---\n".join(formatted)
