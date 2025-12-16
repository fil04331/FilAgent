"""
Runtime metrics for FilAgent - Business and Security Metrics

This module provides agent-level metrics for monitoring:
- Compliance violations and rejections
- Tool execution performance
- Security events (injection attempts, suspicious patterns)
- General agent operations

All metrics follow OpenMetrics standard and ensure no PII in labels.

Usage:
    from runtime.metrics import get_agent_metrics
    
    metrics = get_agent_metrics()
    metrics.record_compliance_rejection(reason="pii_detected", user_id="user123")
    metrics.record_tool_execution(tool_name="calculator", duration_seconds=0.05)
"""

from typing import Optional

# Try to import prometheus_client, but make it optional
try:
    from prometheus_client import Counter, Histogram, Gauge, Info
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    
    # Stub classes for compatibility without prometheus
    class Counter:
        def __init__(self, *args, **kwargs):
            pass
        
        def inc(self, *args, **kwargs):
            pass
        
        def labels(self, *args, **kwargs):
            return self
    
    class Histogram:
        def __init__(self, *args, **kwargs):
            pass
        
        def observe(self, *args, **kwargs):
            pass
        
        def labels(self, *args, **kwargs):
            return self
    
    class Gauge:
        def __init__(self, *args, **kwargs):
            pass
        
        def set(self, *args, **kwargs):
            pass
        
        def inc(self, *args, **kwargs):
            pass
        
        def dec(self, *args, **kwargs):
            pass
        
        def labels(self, *args, **kwargs):
            return self
    
    class Info:
        def __init__(self, *args, **kwargs):
            pass
        
        def info(self, *args, **kwargs):
            pass


class AgentMetrics:
    """
    Agent-level metrics for FilAgent.
    
    Provides business and security metrics for monitoring agent operations,
    compliance enforcement, and potential security threats.
    
    All metrics are designed to be PII-free:
    - User IDs are hashed (not stored directly)
    - Prompt content is never included in labels
    - Only categorical data (reasons, tool names, etc.) in labels
    """
    
    def __init__(self, enabled: bool = True):
        """
        Initialize agent metrics collector.
        
        Args:
            enabled: Enable metrics collection (disabled if Prometheus not available)
        """
        self.enabled = enabled and PROMETHEUS_AVAILABLE
        
        if not self.enabled:
            return
        
        # === Compliance Metrics ===
        
        # Counter: Compliance rejections by reason
        self.filagent_compliance_rejection_total = Counter(
            "filagent_compliance_rejection_total",
            "Total number of compliance rejections by reason (Loi 25/GDPR/AI Act)",
            ["reason", "risk_level", "user_id_hash"],
        )
        
        # Counter: Compliance validations (passed vs rejected)
        self.filagent_compliance_validation_total = Counter(
            "filagent_compliance_validation_total",
            "Total number of compliance validations performed",
            ["status", "risk_level"],  # status: passed, rejected, warning
        )
        
        # Histogram: Compliance validation duration
        self.filagent_compliance_validation_seconds = Histogram(
            "filagent_compliance_validation_seconds",
            "Time spent validating compliance",
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
        )
        
        # === Tool Execution Metrics ===
        
        # Histogram: Tool execution duration
        self.filagent_tool_execution_seconds = Histogram(
            "filagent_tool_execution_seconds",
            "Time spent executing tools",
            ["tool_name", "status"],  # status: success, error, timeout
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0],
        )
        
        # Counter: Tool executions
        self.filagent_tool_execution_total = Counter(
            "filagent_tool_execution_total",
            "Total number of tool executions",
            ["tool_name", "status"],  # status: success, error, timeout
        )
        
        # Counter: Tool validation failures
        self.filagent_tool_validation_failure_total = Counter(
            "filagent_tool_validation_failure_total",
            "Total number of tool validation failures",
            ["tool_name", "error_type"],
        )
        
        # === Security Metrics ===
        
        # Counter: Suspicious patterns detected (potential injection attempts)
        self.filagent_security_suspicious_pattern_total = Counter(
            "filagent_security_suspicious_pattern_total",
            "Total number of suspicious patterns detected in inputs",
            ["pattern_type", "action_taken"],  # pattern_type: sql_injection, command_injection, prompt_injection
        )
        
        # Counter: PII detection events
        self.filagent_security_pii_detected_total = Counter(
            "filagent_security_pii_detected_total",
            "Total number of PII detection events",
            ["pii_type", "action_taken"],  # pii_type: email, phone, ssn, credit_card, etc.
        )
        
        # === Agent Operation Metrics ===
        
        # Counter: Agent conversations
        self.filagent_conversations_total = Counter(
            "filagent_conversations_total",
            "Total number of agent conversations",
            ["status"],  # status: completed, error, timeout
        )
        
        # Histogram: Conversation duration (full reasoning loop)
        self.filagent_conversation_duration_seconds = Histogram(
            "filagent_conversation_duration_seconds",
            "Time spent in conversation reasoning loop",
            ["outcome"],  # outcome: success, max_iterations, error
            buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
        )
        
        # Gauge: Active conversations
        self.filagent_active_conversations = Gauge(
            "filagent_active_conversations",
            "Number of currently active conversations",
        )
        
        # Counter: Reasoning loop iterations
        self.filagent_reasoning_iterations_total = Counter(
            "filagent_reasoning_iterations_total",
            "Total number of reasoning loop iterations",
            ["outcome"],  # outcome: tool_call, final_response, max_iterations
        )
        
        # === Model Metrics ===
        
        # Counter: Token usage
        self.filagent_tokens_total = Counter(
            "filagent_tokens_total",
            "Total number of tokens consumed",
            ["token_type"],  # token_type: prompt, completion
        )
        
        # Histogram: Generation duration
        self.filagent_generation_duration_seconds = Histogram(
            "filagent_generation_duration_seconds",
            "Time spent in LLM generation",
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
        )
        
        # === Info Metrics ===
        
        # Info: Runtime configuration
        self.filagent_info = Info(
            "filagent_info",
            "FilAgent runtime information"
        )
        self.filagent_info.info({
            "version": "1.0.0",
            "module": "runtime",
            "prometheus_available": str(PROMETHEUS_AVAILABLE),
        })
    
    def record_compliance_rejection(
        self,
        reason: str,
        risk_level: str = "MEDIUM",
        user_id: Optional[str] = None,
    ):
        """
        Record a compliance rejection event.
        
        Args:
            reason: Rejection reason (e.g., "pii_detected", "forbidden_pattern", "max_length")
            risk_level: Risk level (LOW, MEDIUM, HIGH, CRITICAL)
            user_id: Optional user ID (will be hashed to prevent PII exposure)
        """
        if not self.enabled:
            return
        
        # Hash user_id to prevent PII in metrics
        user_id_hash = "anonymous"
        if user_id:
            import hashlib
            user_id_hash = hashlib.sha256(user_id.encode()).hexdigest()[:16]
        
        self.filagent_compliance_rejection_total.labels(
            reason=reason,
            risk_level=risk_level,
            user_id_hash=user_id_hash,
        ).inc()
    
    def record_compliance_validation(
        self,
        status: str,
        risk_level: str,
        duration_seconds: float,
    ):
        """
        Record a compliance validation event.
        
        Args:
            status: Validation status (passed, rejected, warning)
            risk_level: Risk level (LOW, MEDIUM, HIGH, CRITICAL)
            duration_seconds: Time spent validating
        """
        if not self.enabled:
            return
        
        self.filagent_compliance_validation_total.labels(
            status=status,
            risk_level=risk_level,
        ).inc()
        
        self.filagent_compliance_validation_seconds.observe(duration_seconds)
    
    def record_tool_execution(
        self,
        tool_name: str,
        duration_seconds: float,
        status: str = "success",
    ):
        """
        Record a tool execution event.
        
        Args:
            tool_name: Name of the tool executed
            duration_seconds: Execution duration
            status: Execution status (success, error, timeout)
        """
        if not self.enabled:
            return
        
        self.filagent_tool_execution_seconds.labels(
            tool_name=tool_name,
            status=status,
        ).observe(duration_seconds)
        
        self.filagent_tool_execution_total.labels(
            tool_name=tool_name,
            status=status,
        ).inc()
    
    def record_tool_validation_failure(
        self,
        tool_name: str,
        error_type: str,
    ):
        """
        Record a tool validation failure.
        
        Args:
            tool_name: Name of the tool
            error_type: Type of validation error (e.g., "missing_argument", "invalid_type")
        """
        if not self.enabled:
            return
        
        self.filagent_tool_validation_failure_total.labels(
            tool_name=tool_name,
            error_type=error_type,
        ).inc()
    
    def record_suspicious_pattern(
        self,
        pattern_type: str,
        action_taken: str = "blocked",
    ):
        """
        Record detection of suspicious pattern (potential injection).
        
        Args:
            pattern_type: Type of pattern (sql_injection, command_injection, prompt_injection)
            action_taken: Action taken (blocked, logged, allowed)
        """
        if not self.enabled:
            return
        
        self.filagent_security_suspicious_pattern_total.labels(
            pattern_type=pattern_type,
            action_taken=action_taken,
        ).inc()
    
    def record_pii_detection(
        self,
        pii_type: str,
        action_taken: str = "masked",
    ):
        """
        Record PII detection event.
        
        Args:
            pii_type: Type of PII detected (email, phone, ssn, credit_card, etc.)
            action_taken: Action taken (masked, blocked, logged)
        """
        if not self.enabled:
            return
        
        self.filagent_security_pii_detected_total.labels(
            pii_type=pii_type,
            action_taken=action_taken,
        ).inc()
    
    def record_conversation(
        self,
        status: str,
        duration_seconds: float,
        outcome: str = "success",
        iterations: int = 1,
    ):
        """
        Record a conversation event.
        
        Args:
            status: Conversation status (completed, error, timeout)
            duration_seconds: Total conversation duration
            outcome: Outcome (success, max_iterations, error)
            iterations: Number of reasoning loop iterations
        """
        if not self.enabled:
            return
        
        self.filagent_conversations_total.labels(status=status).inc()
        self.filagent_conversation_duration_seconds.labels(outcome=outcome).observe(duration_seconds)
        self.filagent_reasoning_iterations_total.labels(outcome=outcome).inc(iterations)
    
    def record_tokens(
        self,
        prompt_tokens: int,
        completion_tokens: int,
    ):
        """
        Record token usage.
        
        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
        """
        if not self.enabled:
            return
        
        self.filagent_tokens_total.labels(token_type="prompt").inc(prompt_tokens)
        self.filagent_tokens_total.labels(token_type="completion").inc(completion_tokens)
    
    def record_generation_duration(
        self,
        duration_seconds: float,
    ):
        """
        Record LLM generation duration.
        
        Args:
            duration_seconds: Generation duration
        """
        if not self.enabled:
            return
        
        self.filagent_generation_duration_seconds.observe(duration_seconds)
    
    def set_active_conversations(self, count: int):
        """
        Set number of active conversations.
        
        Args:
            count: Number of active conversations
        """
        if not self.enabled:
            return
        
        self.filagent_active_conversations.set(count)


# Global singleton instance
_agent_metrics_instance: Optional[AgentMetrics] = None


def get_agent_metrics(enabled: bool = True) -> AgentMetrics:
    """
    Get the global agent metrics instance.
    
    Args:
        enabled: Enable metrics collection
    
    Returns:
        AgentMetrics instance
    """
    global _agent_metrics_instance
    
    if _agent_metrics_instance is None:
        _agent_metrics_instance = AgentMetrics(enabled=enabled)
    
    return _agent_metrics_instance


def reset_agent_metrics():
    """Reset agent metrics instance (useful for testing)."""
    global _agent_metrics_instance
    _agent_metrics_instance = None
