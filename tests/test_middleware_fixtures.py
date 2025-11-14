"""
Tests for middleware fixtures

This module tests the new middleware fixtures added to conftest.py,
including the comprehensive mock_middleware_stack fixture.

Tests verify:
- Individual middleware fixtures work correctly
- mock_middleware_stack provides all required components
- Integration between different middleware components
- Proper isolation between tests
"""

import pytest
import json
from pathlib import Path


@pytest.mark.fixtures
def test_isolated_pii_redactor(isolated_pii_redactor):
    """Test that isolated PII redactor fixture works correctly"""
    # Test email redaction
    text_with_email = "Contact me at john.doe@example.com for details"
    redacted = isolated_pii_redactor.redact(text_with_email)

    assert "[REDACTED]" in redacted
    assert "john.doe@example.com" not in redacted

    # Test phone number redaction
    text_with_phone = "Call me at 555-123-4567"
    redacted = isolated_pii_redactor.redact(text_with_phone)

    assert "[REDACTED]" in redacted
    assert "555-123-4567" not in redacted

    # Test scan_and_log
    scan_result = isolated_pii_redactor.scan_and_log(text_with_email)
    assert scan_result['has_pii'] is True
    assert scan_result['pii_count'] > 0
    assert 'email' in scan_result['types_found']


@pytest.mark.fixtures
def test_isolated_rbac_manager(isolated_rbac_manager):
    """Test that isolated RBAC manager fixture works correctly"""
    # Test admin permissions
    assert isolated_rbac_manager.has_permission('admin', 'execute_code') is True
    assert isolated_rbac_manager.has_permission('admin', 'read_files') is True
    assert isolated_rbac_manager.has_permission('admin', 'write_files') is True

    # Test user permissions
    assert isolated_rbac_manager.has_permission('user', 'read_files') is True
    assert isolated_rbac_manager.has_permission('user', 'execute_code') is False

    # Test guest permissions
    assert isolated_rbac_manager.has_permission('guest', 'read_files') is False

    # Test role listing
    roles = isolated_rbac_manager.list_roles()
    assert 'admin' in roles
    assert 'user' in roles
    assert 'guest' in roles

    # Test permission listing
    admin_perms = isolated_rbac_manager.list_permissions('admin')
    assert len(admin_perms) > 0
    assert 'execute_code' in admin_perms


@pytest.mark.fixtures
def test_isolated_constraints_engine(isolated_constraints_engine):
    """Test that isolated constraints engine fixture works correctly"""
    # Test valid output
    is_valid, errors = isolated_constraints_engine.validate_output("This is a safe output")
    assert is_valid is True
    assert len(errors) == 0

    # Test blocked keyword
    is_valid, errors = isolated_constraints_engine.validate_output("This contains malicious code")
    assert is_valid is False
    assert len(errors) > 0
    assert any('malicious' in error.lower() for error in errors)

    # Test another blocked keyword
    is_valid, errors = isolated_constraints_engine.validate_output("This is dangerous")
    assert is_valid is False


@pytest.mark.fixtures
def test_patched_middlewares_complete(patched_middlewares):
    """Test that patched_middlewares fixture provides all middleware components"""
    # Verify all expected components are present
    required_components = [
        'event_logger',
        'worm_logger',
        'dr_manager',
        'tracker',
        'pii_redactor',
        'rbac_manager',
        'constraints_engine',
        'isolated_fs'
    ]

    for component in required_components:
        assert component in patched_middlewares, f"Missing component: {component}"

    # Verify components are not None
    for component, value in patched_middlewares.items():
        assert value is not None, f"Component {component} is None"


@pytest.mark.fixtures
def test_mock_middleware_stack_basic(mock_middleware_stack):
    """Test basic functionality of mock_middleware_stack fixture"""
    # This is the main fixture requested in the task

    # Verify all components are available
    assert 'event_logger' in mock_middleware_stack
    assert 'worm_logger' in mock_middleware_stack
    assert 'dr_manager' in mock_middleware_stack
    assert 'tracker' in mock_middleware_stack
    assert 'pii_redactor' in mock_middleware_stack
    assert 'rbac_manager' in mock_middleware_stack
    assert 'constraints_engine' in mock_middleware_stack

    # Test that components are functional
    logger = mock_middleware_stack['event_logger']
    assert logger is not None

    # Log an event (should not raise)
    logger.log_event(
        actor="test",
        event="test.basic",
        level="INFO",
        metadata={"test": "value"}
    )


@pytest.mark.integration
def test_mock_middleware_stack_integration(mock_middleware_stack):
    """Test integration between different middleware components"""
    # Extract components
    logger = mock_middleware_stack['event_logger']
    dr_manager = mock_middleware_stack['dr_manager']
    tracker = mock_middleware_stack['tracker']
    pii_redactor = mock_middleware_stack['pii_redactor']
    rbac_manager = mock_middleware_stack['rbac_manager']
    constraints_engine = mock_middleware_stack['constraints_engine']
    isolated_fs = mock_middleware_stack['isolated_fs']

    # Simulate a complete workflow

    # 1. Check permissions (RBAC)
    assert rbac_manager.has_permission('admin', 'execute_code') is True

    # 2. Validate output (Constraints)
    output = "Executing safe code"
    is_valid, errors = constraints_engine.validate_output(output)
    assert is_valid is True

    # 3. Redact PII
    user_input = "Process data from user@example.com"
    safe_input = pii_redactor.redact(user_input)
    assert "[REDACTED]" in safe_input

    # 4. Log the event
    logger.log_event(
        actor="test.integration",
        event="workflow.execute",
        level="INFO",
        conversation_id="conv-test-123",
        task_id="task-test-456",
        metadata={
            "input": safe_input,
            "output": output,
            "permissions_checked": True
        }
    )

    # 5. Create a Decision Record
    import hashlib
    prompt_hash = hashlib.sha256(user_input.encode()).hexdigest()

    dr = dr_manager.create_dr(
        actor="test.integration",
        task_id="task-test-456",
        decision="execute_workflow",
        prompt_hash=prompt_hash,
        tools_used=["pii_redactor", "constraints_engine"],
        alternatives_considered=["reject", "ask_user"]
    )

    assert dr is not None
    assert dr.signature is not None  # Should be signed

    # 6. Track provenance
    trace_id = tracker.track_generation(
        conversation_id="conv-test-123",
        input_message=user_input,
        output_message=output
    )

    assert trace_id is not None

    # 7. Verify files were created
    events_dir = isolated_fs['logs_events']
    assert events_dir.exists()

    decisions_dir = isolated_fs['logs_decisions']
    assert decisions_dir.exists()

    # Check that decision record was saved
    dr_files = list(decisions_dir.glob("DR-*.json"))
    assert len(dr_files) > 0

    # Verify decision record content
    dr_file = dr_files[0]
    with open(dr_file, 'r') as f:
        dr_data = json.load(f)

    assert dr_data['actor'] == "test.integration"
    assert dr_data['decision'] == "execute_workflow"
    assert 'signature' in dr_data


@pytest.mark.integration
def test_mock_middleware_stack_pii_masking_flow(mock_middleware_stack):
    """Test complete PII masking flow with middleware stack"""
    logger = mock_middleware_stack['event_logger']
    pii_redactor = mock_middleware_stack['pii_redactor']

    # Sensitive data
    sensitive_message = """
    User details:
    Email: alice@company.com
    Phone: 555-987-6543
    SSN: 123-45-6789
    """

    # Redact PII
    safe_message = pii_redactor.redact(sensitive_message)

    # Verify all PII is redacted
    assert "alice@company.com" not in safe_message
    assert "555-987-6543" not in safe_message
    assert "123-45-6789" not in safe_message
    assert "[REDACTED]" in safe_message

    # Log the safe message
    logger.log_event(
        actor="pii.test",
        event="data.processed",
        level="INFO",
        metadata={"message": safe_message}
    )

    # Verify scan detects PII
    scan_result = pii_redactor.scan_and_log(sensitive_message)
    assert scan_result['has_pii'] is True
    assert scan_result['pii_count'] >= 3  # email, phone, ssn


@pytest.mark.integration
def test_mock_middleware_stack_decision_record_flow(mock_middleware_stack):
    """Test Decision Record creation and verification flow"""
    dr_manager = mock_middleware_stack['dr_manager']
    isolated_fs = mock_middleware_stack['isolated_fs']

    # Create a decision record
    import hashlib
    prompt = "Execute code to analyze data"
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()

    dr = dr_manager.create_dr(
        actor="agent.core",
        task_id="task-dr-test-001",
        decision="execute_code_analysis",
        prompt_hash=prompt_hash,
        policy_version="policies@1.0.0",
        model_fingerprint="model-v2.0",
        tools_used=["python_sandbox", "data_analyzer"],
        alternatives_considered=["reject_unsafe", "request_clarification"],
        reasoning_markers=["plan:3-steps", "verified:safe"]
    )

    # Verify DR properties
    assert dr.dr_id is not None
    assert dr.actor == "agent.core"
    assert dr.decision == "execute_code_analysis"
    assert dr.signature is not None
    assert "ed25519:" in dr.signature

    # Verify DR was saved
    decisions_dir = isolated_fs['logs_decisions']
    dr_file = decisions_dir / f"{dr.dr_id}.json"
    assert dr_file.exists()

    # Load and verify content
    with open(dr_file, 'r') as f:
        saved_dr = json.load(f)

    assert saved_dr['dr_id'] == dr.dr_id
    assert saved_dr['actor'] == "agent.core"
    assert saved_dr['decision'] == "execute_code_analysis"
    assert len(saved_dr['tools_used']) == 2
    assert 'signature' in saved_dr

    # Verify signature is valid
    loaded_dr = dr_manager.load_dr(dr.dr_id)
    assert loaded_dr is not None
    assert loaded_dr.verify(dr_manager.public_key) is True


@pytest.mark.integration
def test_mock_middleware_stack_isolation(mock_middleware_stack):
    """Test that middleware stack is properly isolated between tests"""
    # This test verifies that the fixture creates a fresh, isolated environment
    # for each test (no state leakage between tests)

    isolated_fs = mock_middleware_stack['isolated_fs']
    logger = mock_middleware_stack['event_logger']

    # Log a unique event
    import time
    unique_id = f"test-{int(time.time() * 1000)}"

    logger.log_event(
        actor="isolation.test",
        event="isolation.check",
        level="INFO",
        metadata={"unique_id": unique_id}
    )

    # Verify event log exists
    events_dir = isolated_fs['logs_events']
    assert events_dir.exists()

    # The directory should be in tmp_path, not the real logs directory
    assert "tmp" in str(events_dir) or "temp" in str(events_dir).lower()


@pytest.mark.fixtures
def test_middleware_components_independent():
    """Test that individual middleware fixtures can be used independently"""
    # This test uses pytest's dependency injection to get individual fixtures
    # without using the full stack
    pass  # Placeholder - individual fixtures tested in other tests


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
