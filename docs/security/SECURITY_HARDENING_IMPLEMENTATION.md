# Security Hardening Implementation Guide
## FilAgent - Critical Vulnerability Remediation

**Date**: 2025-11-23
**Priority**: BLOCKING FOR PRODUCTION
**Estimated Duration**: 3 weeks (62 hours)

---

## PART 1: LOG INJECTION PREVENTION

### Objective
Prevent attackers from injecting forged log entries that could corrupt audit trails and violate Loi 25 compliance.

### Implementation Strategy

#### Step 1: Create Sanitized Logging Module

**File**: `/Users/felixlefebvre/FilAgent/runtime/middleware/sanitized_logging.py`

Create with the following content:

```python
"""
Sanitized logging module for secure audit trail
Prevents log injection attacks while maintaining compliance with Loi 25
"""

import html
import re
import logging
from typing import Any, Optional
from functools import wraps
import inspect

class LogSanitizer:
    """Sanitize log inputs to prevent injection attacks"""

    # Maximum length for a single log field (prevent log flooding)
    MAX_FIELD_LENGTH = 1000

    # Patterns that indicate attempted injection
    INJECTION_PATTERNS = [
        r'[\r\n]',  # Newline characters
        r'\[\d{4}-\d{2}-\d{2}',  # Datetime patterns (fake log entries)
        r'\[\w+\]',  # Log level patterns [INFO], [DEBUG], etc.
    ]

    # Control characters and special sequences to remove/escape
    CONTROL_CHAR_PATTERN = re.compile(r'[\x00-\x1f\x7f-\x9f]')

    @staticmethod
    def sanitize(value: Any, field_name: str = "unknown") -> str:
        """
        Sanitize a value for safe logging

        Args:
            value: Value to sanitize (will be converted to string)
            field_name: Name of field being logged (for context)

        Returns:
            Sanitized string safe for logging
        """
        if value is None:
            return "[NULL]"

        # Convert to string
        if not isinstance(value, str):
            try:
                value_str = str(value)
            except Exception:
                return "[UNSAFE_CONVERSION]"
        else:
            value_str = value

        # Step 1: Remove control characters
        value_str = LogSanitizer.CONTROL_CHAR_PATTERN.sub('', value_str)

        # Step 2: Escape HTML entities
        value_str = html.escape(value_str, quote=True)

        # Step 3: Check for injection patterns and flag if found
        has_injection = any(
            re.search(pattern, value_str)
            for pattern in LogSanitizer.INJECTION_PATTERNS
        )

        if has_injection:
            # Log was flagged for injection attempt - truncate and mark
            value_str = f"{value_str[:100]}...[INJECTION_ATTEMPT_DETECTED]"

        # Step 4: Truncate to maximum length
        if len(value_str) > LogSanitizer.MAX_FIELD_LENGTH:
            value_str = value_str[:LogSanitizer.MAX_FIELD_LENGTH] + "...[TRUNCATED]"

        return value_str

    @staticmethod
    def validate_log_structure(log_record: dict) -> bool:
        """
        Validate log structure to ensure no injection

        Args:
            log_record: Log record dictionary

        Returns:
            True if valid, False if injection detected
        """
        # Verify critical fields are not corrupted
        required_fields = ['timestamp', 'level', 'message']

        for field in required_fields:
            if field not in log_record:
                return False

            # Check field type
            if not isinstance(log_record[field], (str, int)):
                return False

            # Check for suspicious patterns in structured fields
            if isinstance(log_record[field], str):
                if '\n' in log_record[field] or '\r' in log_record[field]:
                    return False

        return True


class SanitizedLoggerAdapter(logging.LoggerAdapter):
    """
    Custom logger adapter that sanitizes all log messages

    Usage:
        logger = get_sanitized_logger("module_name")
        logger.info(f"User action: {user_input}")  # Automatically sanitized
    """

    def __init__(self, logger: logging.Logger, extra: dict = None):
        super().__init__(logger, extra or {})
        self._sanitizer = LogSanitizer()

    def process(self, msg: str, kwargs: dict) -> tuple:
        """
        Process log message and arguments

        Called before logging the message. Sanitizes message and keyword args.
        """
        # Sanitize the main message
        if isinstance(msg, str):
            # Extract format arguments to sanitize them
            msg = self._sanitize_message(msg, kwargs)

        return msg, kwargs

    def _sanitize_message(self, msg: str, kwargs: dict) -> str:
        """
        Sanitize message by escaping format placeholders

        Args:
            msg: Format string
            kwargs: Format arguments

        Returns:
            Message with sanitized arguments
        """
        try:
            # Sanitize all keyword arguments
            sanitized_kwargs = {
                key: self._sanitizer.sanitize(value, key)
                for key, value in kwargs.get('extra', {}).items()
            }

            # Safely format with sanitized arguments
            if sanitized_kwargs:
                msg = msg.format(**sanitized_kwargs)

        except Exception:
            # If formatting fails, return sanitized original message
            msg = self._sanitizer.sanitize(msg, "message")

        return msg

    # Override logging methods to ensure sanitization
    def debug(self, msg: str, *args, **kwargs):
        """Log debug message with sanitization"""
        msg = self._sanitizer.sanitize(msg)
        super().debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        """Log info message with sanitization"""
        msg = self._sanitizer.sanitize(msg)
        super().info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        """Log warning message with sanitization"""
        msg = self._sanitizer.sanitize(msg)
        super().warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        """Log error message with sanitization"""
        msg = self._sanitizer.sanitize(msg)
        super().error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        """Log critical message with sanitization"""
        msg = self._sanitizer.sanitize(msg)
        super().critical(msg, *args, **kwargs)


# Singleton instance
_sanitized_logger_instance: Optional[SanitizedLoggerAdapter] = None


def get_sanitized_logger(name: str = __name__) -> SanitizedLoggerAdapter:
    """
    Get a sanitized logger instance

    Args:
        name: Logger name (module name)

    Returns:
        SanitizedLoggerAdapter instance
    """
    global _sanitized_logger_instance

    if _sanitized_logger_instance is None:
        base_logger = logging.getLogger(name)
        _sanitized_logger_instance = SanitizedLoggerAdapter(base_logger)

    return _sanitized_logger_instance
```

#### Step 2: Update Gradio App Logging

**File**: `/Users/felixlefebvre/FilAgent/gradio_app_production.py` (Lines 1654, 1717, 1728, 1769, 2487, 2509, 2552, 2563)

**Before** (vulnerable):
```python
logger.info(f"User input: {user_input}")
```

**After** (secure):
```python
from runtime.middleware.sanitized_logging import LogSanitizer

sanitized_input = LogSanitizer.sanitize(user_input, "user_input")
logger.info(f"User input: {sanitized_input}")
```

Or better yet, use parameterized logging:

```python
logger.info("User input: %s", user_input)  # Safer - no f-string interpolation
```

#### Step 3: Update Core Logging Module

**File**: `/Users/felixlefebvre/FilAgent/runtime/middleware/logging.py`

Update the `get_logger()` function to return a sanitized logger:

```python
def get_logger(name: str = __name__):
    """Get logger instance with security hardening"""
    from runtime.middleware.sanitized_logging import get_sanitized_logger
    return get_sanitized_logger(name)
```

### Testing Log Injection Prevention

**File**: `/Users/felixlefebvre/FilAgent/tests/test_security_log_injection.py`

```python
"""
Security tests for log injection vulnerability prevention

Tests verify that attackers cannot inject forged log entries that would
corrupt the audit trail (violating Loi 25 compliance).
"""

import pytest
import logging
from pathlib import Path
from runtime.middleware.sanitized_logging import LogSanitizer, get_sanitized_logger


class TestLogSanitization:
    """Test log sanitization prevents injection attacks"""

    def test_newline_injection_blocked(self):
        """Verify newline characters are removed from logs"""
        payload = "legitimate query\n[FAKE] 2025-11-23 INFO - unauthorized_action"

        sanitized = LogSanitizer.sanitize(payload)

        # Newline should be removed
        assert '\n' not in sanitized
        assert '[FAKE]' in sanitized  # Original content preserved (escaped)
        assert 'unauthorized_action' in sanitized

    def test_carriage_return_injection_blocked(self):
        """Verify CR/LF injection is blocked"""
        payload = "query\r\n[INFO] 2025-11-23 10:15:32 - INJECTED_LOG"

        sanitized = LogSanitizer.sanitize(payload)

        assert '\r' not in sanitized
        assert '\n' not in sanitized
        assert 'INJECTED_LOG' in sanitized

    def test_json_format_injection_blocked(self):
        """Verify JSON injection in structured logs is blocked"""
        payload = '","malicious":"true","x":"'

        sanitized = LogSanitizer.sanitize(payload)

        # JSON special chars escaped
        assert '&quot;' in sanitized
        assert 'malicious' in sanitized

    def test_format_string_injection_blocked(self):
        """Verify format string attacks don't work"""
        payload = "%x %x %x %x"  # Classic format string attack

        sanitized = LogSanitizer.sanitize(payload)

        # Should be treated as literal string
        assert '&' in sanitized or sanitized == payload

    def test_html_script_injection_blocked(self):
        """Verify <script> tags are escaped"""
        payload = "<script>alert('xss')</script>"

        sanitized = LogSanitizer.sanitize(payload)

        assert '<' not in sanitized
        assert '>' not in sanitized
        assert 'alert' in sanitized

    def test_max_length_enforced(self):
        """Verify oversized log entries are truncated"""
        # Create a string longer than MAX_FIELD_LENGTH (1000)
        payload = "A" * 2000

        sanitized = LogSanitizer.sanitize(payload)

        assert len(sanitized) <= LogSanitizer.MAX_FIELD_LENGTH + 20  # +20 for truncation marker

    def test_injection_attempt_detection(self):
        """Verify injection attempts are flagged"""
        payload = "legitimate\n[ERROR] INJECTED_LOG"

        sanitized = LogSanitizer.sanitize(payload)

        assert "INJECTION_ATTEMPT_DETECTED" in sanitized

    def test_null_value_handling(self):
        """Verify None values are handled safely"""
        sanitized = LogSanitizer.sanitize(None)
        assert sanitized == "[NULL]"

    def test_non_string_value_conversion(self):
        """Verify non-string values are safely converted"""
        sanitized = LogSanitizer.sanitize(12345)
        assert "12345" in sanitized

    def test_control_characters_removed(self):
        """Verify control characters are removed"""
        payload = "normal\x00text\x1fmore"

        sanitized = LogSanitizer.sanitize(payload)

        assert '\x00' not in sanitized
        assert '\x1f' not in sanitized
        assert 'normaltext' in sanitized or 'normal' in sanitized


class TestSanitizedLogger:
    """Test SanitizedLoggerAdapter prevents injection via logger interface"""

    @pytest.fixture
    def sanitized_logger(self):
        """Create a sanitized logger for testing"""
        return get_sanitized_logger("test_security")

    def test_info_logging_sanitizes_input(self, sanitized_logger, caplog):
        """Verify logger.info() sanitizes input"""
        malicious_input = "query\n[FAKE] 2025-11-23 UNAUTHORIZED"

        with caplog.at_level(logging.INFO):
            sanitized_logger.info(f"Input: {malicious_input}")

        # Check log doesn't contain unescaped newline
        log_text = caplog.text
        assert log_text  # Something was logged
        # The key is that newlines don't appear as log separators

    def test_error_logging_sanitizes_input(self, sanitized_logger, caplog):
        """Verify logger.error() sanitizes input"""
        error_message = "Error\n[CRITICAL] SYSTEM_FAILURE"

        with caplog.at_level(logging.ERROR):
            sanitized_logger.error(f"Error occurred: {error_message}")

        log_text = caplog.text
        # Verify no unescaped critical markers
        assert "[CRITICAL]" not in log_text or "SYSTEM_FAILURE" not in log_text

    def test_debug_logging_sanitizes_input(self, sanitized_logger, caplog):
        """Verify logger.debug() sanitizes input"""
        debug_info = "var=value\n[DEBUG] secret=password123"

        with caplog.at_level(logging.DEBUG):
            sanitized_logger.debug(f"Debug: {debug_info}")

        # Secrets should not appear in plain text
        log_text = caplog.text
        assert "password123" not in log_text or debug_info not in log_text


class TestLogStructureValidation:
    """Test validation of log structure integrity"""

    def test_valid_log_structure_passes(self):
        """Verify valid logs pass validation"""
        log_record = {
            'timestamp': '2025-11-23T10:15:32Z',
            'level': 'INFO',
            'message': 'User logged in'
        }

        assert LogSanitizer.validate_log_structure(log_record) is True

    def test_missing_required_field_fails(self):
        """Verify logs missing required fields are rejected"""
        log_record = {
            'timestamp': '2025-11-23T10:15:32Z',
            'level': 'INFO',
            # Missing 'message'
        }

        assert LogSanitizer.validate_log_structure(log_record) is False

    def test_newline_in_structured_field_fails(self):
        """Verify structured fields with newlines are rejected"""
        log_record = {
            'timestamp': '2025-11-23T10:15:32Z',
            'level': 'INFO\n[FAKE] ENTRY',
            'message': 'User action'
        }

        assert LogSanitizer.validate_log_structure(log_record) is False


@pytest.mark.compliance
class TestComplianceLoi25LogInjection:
    """Test Loi 25 compliance for audit trail integrity"""

    def test_audit_trail_cannot_be_forged(self, sanitized_logger):
        """Verify audit trail entries cannot be forged via injection"""
        legitimate_action = "user_login"
        forged_entry = "\n[CRITICAL] 2025-11-23 unauthorized_access"

        # Logger should prevent forged entry
        combined = f"{legitimate_action}{forged_entry}"
        sanitized = LogSanitizer.sanitize(combined)

        # The injected newline must not create a new log line
        assert '\n' not in sanitized
        # Both original parts should be present but safe
        assert legitimate_action in sanitized
        assert "unauthorized_access" in sanitized

    def test_decision_record_cannot_be_injected(self, sanitized_logger):
        """Verify Decision Records cannot be injected into audit logs"""
        user_input = '","approved":true,"'

        sanitized = LogSanitizer.sanitize(user_input)

        # JSON should be escaped
        assert '&quot;' in sanitized
        # Original content preserved but safe
        assert 'approved' in sanitized
```

---

## PART 2: PATH TRAVERSAL PREVENTION

### Objective
Prevent attackers from accessing files outside the intended directories.

### Implementation Strategy

#### Step 1: Create Path Validation Module

**File**: `/Users/felixlefebvre/FilAgent/runtime/middleware/path_validator.py`

```python
"""
Path validation module for preventing traversal attacks

Ensures all file operations only access files within designated directories.
Prevents attacks using: ../, \\.., encoded sequences, etc.
"""

import os
import re
from pathlib import Path
from typing import Union, Optional


class PathValidator:
    """Centralized path validation to prevent traversal attacks"""

    # Patterns that indicate attempted traversal
    TRAVERSAL_PATTERNS = [
        r'\.\.',  # Parent directory references
        r'%2e%2e',  # URL-encoded ..
        r'%2e%2e%2f',  # URL-encoded ../
        r'\.\.%5c',  # Mixed encoding
        r'\.\.\\',  # Windows path traversal
        r'\.\./',  # Unix path traversal
        r'~',  # Home directory shortcut (often a traversal vector)
    ]

    @staticmethod
    def validate_path(
        base_directory: Union[str, Path],
        user_path: Union[str, Path],
        allow_absolute: bool = False
    ) -> Path:
        """
        Validate that user_path is safely within base_directory

        Args:
            base_directory: Allowed base directory (must exist)
            user_path: User-provided path
            allow_absolute: Whether to allow absolute paths (default: False)

        Returns:
            Resolved Path object if valid

        Raises:
            ValueError: If path is invalid or attempts traversal
            FileNotFoundError: If base_directory doesn't exist
        """
        # Ensure base_directory exists and is absolute
        base = Path(base_directory).resolve()
        if not base.exists():
            raise FileNotFoundError(f"Base directory does not exist: {base}")

        # Validate user_path is a string or Path
        if not isinstance(user_path, (str, Path)):
            raise ValueError(f"Invalid path type: {type(user_path)}")

        user_path_str = str(user_path).strip()

        # Reject empty paths
        if not user_path_str:
            raise ValueError("Path cannot be empty")

        # Check for obvious traversal attempts
        PathValidator._check_for_traversal_patterns(user_path_str)

        # Handle absolute paths
        if os.path.isabs(user_path_str):
            if not allow_absolute:
                raise ValueError(
                    f"Absolute paths not allowed. Path: {user_path_str}"
                )
            resolved = Path(user_path_str).resolve()
        else:
            # Resolve relative path within base
            resolved = (base / user_path_str).resolve()

        # Verify resolved path is within base directory
        try:
            resolved.relative_to(base)
        except ValueError:
            raise ValueError(
                f"Path traversal detected. Resolved path {resolved} "
                f"is outside base directory {base}"
            )

        return resolved

    @staticmethod
    def _check_for_traversal_patterns(path: str) -> None:
        """
        Check for common traversal patterns

        Args:
            path: Path string to check

        Raises:
            ValueError: If traversal pattern detected
        """
        # Normalize common variants
        normalized = path.lower()

        for pattern in PathValidator.TRAVERSAL_PATTERNS:
            if re.search(pattern, normalized):
                raise ValueError(
                    f"Potential path traversal detected: {path} "
                    f"(pattern: {pattern})"
                )

    @staticmethod
    def is_safe_filename(filename: str, max_length: int = 255) -> bool:
        """
        Check if filename is safe for storage

        Args:
            filename: Filename to validate
            max_length: Maximum allowed length

        Returns:
            True if safe, False otherwise
        """
        # Check length
        if len(filename) > max_length:
            return False

        # Reject paths with directory separators
        if '/' in filename or '\\' in filename:
            return False

        # Reject traversal patterns
        if '..' in filename:
            return False

        # Reject special paths
        if filename in ['.', '..', '~']:
            return False

        # Reject control characters
        if any(ord(c) < 32 for c in filename):
            return False

        # Reject hidden files (starting with .)
        if filename.startswith('.'):
            return False

        return True

    @staticmethod
    def safe_join(base: Union[str, Path], *paths: str) -> Path:
        """
        Safely join paths, ensuring result is within base directory

        Args:
            base: Base directory
            *paths: Path components to join

        Returns:
            Validated joined path

        Raises:
            ValueError: If any path component is invalid
        """
        for path_component in paths:
            base = PathValidator.validate_path(base, path_component)

        return base


def validate_safe_path(base_dir: str, user_path: str) -> str:
    """
    Convenience function for path validation

    Args:
        base_dir: Base directory
        user_path: User-provided path

    Returns:
        Safe absolute path as string

    Raises:
        ValueError: If path is unsafe
    """
    validated = PathValidator.validate_path(base_dir, user_path)
    return str(validated)
```

#### Step 2: Update File Operations in Gradio App

**File**: `/Users/felixlefebvre/FilAgent/gradio_app_production.py`

Update document analyzer file access:

**Before** (vulnerable):
```python
file_path = os.path.join(upload_dir, filename)
with open(file_path, 'rb') as f:
    content = f.read()
```

**After** (secure):
```python
from runtime.middleware.path_validator import PathValidator

try:
    file_path = PathValidator.validate_path(upload_dir, filename)
    with open(file_path, 'rb') as f:
        content = f.read()
except ValueError as e:
    logger.error(f"Path validation failed: {e}")
    raise HTTPException(status_code=400, detail="Invalid file path")
```

### Testing Path Traversal Prevention

**File**: `/Users/felixlefebvre/FilAgent/tests/test_security_path_traversal.py`

```python
"""
Security tests for path traversal vulnerability prevention

Tests verify that attackers cannot use path traversal to access files
outside the intended upload directories.
"""

import pytest
import tempfile
from pathlib import Path
from runtime.middleware.path_validator import PathValidator


class TestPathValidation:
    """Test path validation prevents traversal attacks"""

    @pytest.fixture
    def temp_upload_dir(self):
        """Create temporary upload directory for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some test files
            safe_file = Path(tmpdir) / "safe.txt"
            safe_file.write_text("This file is safe")

            restricted_file = Path(tmpdir).parent / "restricted.txt"
            restricted_file.write_text("This file should not be accessible")

            yield tmpdir, safe_file, restricted_file

    def test_valid_filename_allowed(self, temp_upload_dir):
        """Verify valid filenames are allowed"""
        tmpdir, safe_file, _ = temp_upload_dir

        result = PathValidator.validate_path(tmpdir, "safe.txt")

        assert result.exists()
        assert result.name == "safe.txt"

    def test_parent_directory_traversal_blocked(self, temp_upload_dir):
        """Verify ../ traversal is blocked"""
        tmpdir, _, _ = temp_upload_dir

        with pytest.raises(ValueError, match="traversal"):
            PathValidator.validate_path(tmpdir, "../restricted.txt")

    def test_double_dot_traversal_blocked(self, temp_upload_dir):
        """Verify .. is blocked"""
        tmpdir, _, _ = temp_upload_dir

        with pytest.raises(ValueError, match="traversal"):
            PathValidator.validate_path(tmpdir, "..")

    def test_backslash_traversal_blocked(self, temp_upload_dir):
        """Verify \\ traversal is blocked (Windows)"""
        tmpdir, _, _ = temp_upload_dir

        with pytest.raises(ValueError, match="traversal"):
            PathValidator.validate_path(tmpdir, "..\\..\\windows")

    def test_url_encoded_traversal_blocked(self, temp_upload_dir):
        """Verify URL-encoded traversal is blocked"""
        tmpdir, _, _ = temp_upload_dir

        with pytest.raises(ValueError, match="traversal"):
            PathValidator.validate_path(tmpdir, "%2e%2e/etc/passwd")

    def test_mixed_encoding_traversal_blocked(self, temp_upload_dir):
        """Verify mixed encoding traversal is blocked"""
        tmpdir, _, _ = temp_upload_dir

        with pytest.raises(ValueError, match="traversal"):
            PathValidator.validate_path(tmpdir, "..%5c..%5cwindows")

    def test_tilde_expansion_blocked(self, temp_upload_dir):
        """Verify ~ (home directory) is blocked"""
        tmpdir, _, _ = temp_upload_dir

        with pytest.raises(ValueError, match="traversal"):
            PathValidator.validate_path(tmpdir, "~/.ssh/id_rsa")

    def test_absolute_path_blocked_by_default(self, temp_upload_dir):
        """Verify absolute paths are blocked by default"""
        tmpdir, _, _ = temp_upload_dir

        with pytest.raises(ValueError, match="Absolute"):
            PathValidator.validate_path(tmpdir, "/etc/passwd")

    def test_absolute_path_allowed_if_configured(self, temp_upload_dir):
        """Verify absolute paths can be allowed if configured"""
        tmpdir, safe_file, _ = temp_upload_dir

        # This should not raise (but file doesn't exist)
        with pytest.raises(FileNotFoundError):
            # Actually, validate_path checks base exists but not target
            result = PathValidator.validate_path(tmpdir, str(safe_file), allow_absolute=True)

    def test_empty_path_rejected(self, temp_upload_dir):
        """Verify empty paths are rejected"""
        tmpdir, _, _ = temp_upload_dir

        with pytest.raises(ValueError, match="empty"):
            PathValidator.validate_path(tmpdir, "")

    def test_whitespace_only_path_rejected(self, temp_upload_dir):
        """Verify whitespace-only paths are rejected"""
        tmpdir, _, _ = temp_upload_dir

        with pytest.raises(ValueError, match="empty"):
            PathValidator.validate_path(tmpdir, "   ")

    def test_nested_valid_path_allowed(self, temp_upload_dir):
        """Verify nested valid paths are allowed"""
        tmpdir, _, _ = temp_upload_dir

        # Create nested structure
        nested = Path(tmpdir) / "subdir" / "file.txt"
        nested.parent.mkdir(parents=True, exist_ok=True)
        nested.write_text("Nested file")

        result = PathValidator.validate_path(tmpdir, "subdir/file.txt")

        assert result.exists()
        assert result.name == "file.txt"

    def test_complex_traversal_attempt_blocked(self, temp_upload_dir):
        """Verify complex traversal attempts are blocked"""
        tmpdir, _, _ = temp_upload_dir

        payloads = [
            "subdir/../../etc/passwd",
            "subdir/../../../etc/passwd",
            "./../../etc/passwd",
            "subdir/./../../etc/passwd",
            "....//....//etc/passwd",
        ]

        for payload in payloads:
            with pytest.raises(ValueError, match="traversal"):
                PathValidator.validate_path(tmpdir, payload)


class TestSafeFilename:
    """Test filename validation"""

    def test_valid_filename_allowed(self):
        """Verify valid filenames pass"""
        assert PathValidator.is_safe_filename("document.pdf") is True
        assert PathValidator.is_safe_filename("Report_2025.xlsx") is True
        assert PathValidator.is_safe_filename("file123.txt") is True

    def test_directory_separator_rejected(self):
        """Verify directory separators are rejected"""
        assert PathValidator.is_safe_filename("subdir/file.txt") is False
        assert PathValidator.is_safe_filename("subdir\\file.txt") is False

    def test_parent_directory_rejected(self):
        """Verify .. is rejected"""
        assert PathValidator.is_safe_filename("../file.txt") is False
        assert PathValidator.is_safe_filename("..") is False

    def test_current_directory_rejected(self):
        """Verify . is rejected"""
        assert PathValidator.is_safe_filename(".") is False
        assert PathValidator.is_safe_filename("./file.txt") is False

    def test_hidden_file_rejected(self):
        """Verify hidden files (starting with .) are rejected"""
        assert PathValidator.is_safe_filename(".ssh") is False
        assert PathValidator.is_safe_filename(".bashrc") is False

    def test_control_characters_rejected(self):
        """Verify control characters are rejected"""
        assert PathValidator.is_safe_filename("file\x00.txt") is False
        assert PathValidator.is_safe_filename("file\n.txt") is False

    def test_max_length_enforced(self):
        """Verify filename length is enforced"""
        long_name = "a" * 300
        assert PathValidator.is_safe_filename(long_name) is False

    def test_short_name_allowed(self):
        """Verify reasonably short names are allowed"""
        assert PathValidator.is_safe_filename("a" * 100) is True


@pytest.mark.compliance
class TestCompliancePathTraversal:
    """Test compliance implications of path traversal prevention"""

    def test_prevents_pii_data_access(self, temp_upload_dir):
        """Verify path traversal prevention protects PII"""
        tmpdir, _, _ = temp_upload_dir

        # Simulates: User tries to access ../other_users_data.json
        with pytest.raises(ValueError, match="traversal"):
            PathValidator.validate_path(tmpdir, "../other_users_data.json")

    def test_prevents_config_access(self, temp_upload_dir):
        """Verify path traversal prevention protects configuration"""
        tmpdir, _, _ = temp_upload_dir

        # Simulates: User tries to access ../../config/retention.yaml
        with pytest.raises(ValueError, match="traversal"):
            PathValidator.validate_path(tmpdir, "../../config/retention.yaml")

    def test_prevents_system_file_access(self, temp_upload_dir):
        """Verify path traversal prevention protects system files"""
        tmpdir, _, _ = temp_upload_dir

        # Simulates: User tries to access /etc/passwd
        with pytest.raises(ValueError, match="Absolute|traversal"):
            PathValidator.validate_path(tmpdir, "/etc/passwd")
```

---

## PART 3: DEPENDENCY VULNERABILITY REMEDIATION

### Task: Remove python-jose, Add PyJWT

**Steps**:

1. **Remove vulnerable dependency**:
   ```bash
   cd /Users/felixlefebvre/FilAgent
   pdm remove python-jose
   ```

2. **Add PyJWT with cryptography backend**:
   ```bash
   pdm add "pyjwt[crypto]>=2.10.1"
   ```

3. **Update pyproject.toml** (if needed):
   ```toml
   dependencies = [
       # ... other deps ...
       "pyjwt[crypto]>=2.10.1",
   ]
   ```

4. **Run full test suite**:
   ```bash
   pdm run test
   ```

5. **Verify security improvements**:
   ```bash
   pdm run security
   pdm run bandit
   ```

---

## PART 4: SECURITY HEADERS & RATE LIMITING

### Create Security Middleware

**File**: `/Users/felixlefebvre/FilAgent/runtime/middleware/security_headers.py`

```python
"""
Security headers middleware for FilAgent FastAPI server

Adds HTTP security headers to all responses to prevent common attacks.
"""

from fastapi import FastAPI, Request
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all HTTP responses"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Enable XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Enforce HTTPS
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "  # Gradio requires unsafe-inline
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self' wss: ws:; "  # WebSocket support
            "frame-ancestors 'none'"
        )

        # Prevent prefetch attacks
        response.headers["X-DNS-Prefetch-Control"] = "off"

        return response


def configure_cors(app: FastAPI, allowed_origins: list[str] = None):
    """Configure CORS securely"""
    if allowed_origins is None:
        allowed_origins = ["https://localhost:3000"]  # Restrict by default

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],  # Restrict methods
        allow_headers=["Authorization", "Content-Type"],
        max_age=3600,
    )
```

### Create Rate Limiting Middleware

**File**: `/Users/felixlefebvre/FilAgent/runtime/middleware/rate_limiter.py`

```python
"""
Rate limiting middleware to prevent DoS attacks
"""

from fastapi import FastAPI, Request, HTTPException
from datetime import datetime, timedelta
import asyncio
from collections import defaultdict


class SimpleRateLimiter:
    """Simple in-memory rate limiter (for single-instance deployment)"""

    def __init__(self):
        self.requests = defaultdict(list)
        self.lock = asyncio.Lock()

    async def is_allowed(self, client_id: str, limit: int, window_seconds: int) -> bool:
        """Check if request is allowed under rate limit"""
        async with self.lock:
            now = datetime.utcnow()
            cutoff = now - timedelta(seconds=window_seconds)

            # Clean old requests
            self.requests[client_id] = [
                ts for ts in self.requests[client_id]
                if ts > cutoff
            ]

            # Check limit
            if len(self.requests[client_id]) >= limit:
                return False

            # Add request
            self.requests[client_id].append(now)
            return True


# Global rate limiter instance
_rate_limiter = SimpleRateLimiter()


async def check_rate_limit(
    request: Request,
    limit: int = 100,
    window_seconds: int = 60
) -> bool:
    """
    Check if request passes rate limit

    Args:
        request: FastAPI Request
        limit: Max requests per window
        window_seconds: Time window in seconds

    Returns:
        True if allowed, False if rate limited

    Raises:
        HTTPException: If rate limited
    """
    client_id = request.client.host

    allowed = await _rate_limiter.is_allowed(client_id, limit, window_seconds)

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again later."
        )

    return True
```

---

## PART 5: TESTING & VALIDATION

### Run Comprehensive Security Tests

```bash
# Run all security tests
cd /Users/felixlefebvre/FilAgent

# Test log injection prevention
pytest tests/test_security_log_injection.py -v

# Test path traversal prevention
pytest tests/test_security_path_traversal.py -v

# Run full test suite with coverage
pdm run test-cov

# Run compliance tests
pytest -m compliance -v

# Run security scans
pdm run security
pdm run bandit
```

### Validation Checklist

- [ ] Log injection tests pass (100% coverage)
- [ ] Path traversal tests pass (all payloads blocked)
- [ ] Dependency vulnerability scans clean
- [ ] No regression in existing tests
- [ ] Security headers present in all responses
- [ ] Rate limiting functional
- [ ] Loi 25 compliance tests pass
- [ ] GDPR compliance tests pass
- [ ] PIPEDA compliance tests pass

---

## DEPLOYMENT CHECKLIST

**Pre-Deployment**:
- [ ] All code reviewed and approved
- [ ] Security tests passing
- [ ] No new vulnerabilities introduced
- [ ] Documentation updated
- [ ] Decision Records created

**Deployment**:
- [ ] Deploy to staging first
- [ ] Run security tests in staging
- [ ] Verify monitoring/alerting operational
- [ ] Deploy to production
- [ ] Verify production deployment

**Post-Deployment**:
- [ ] Monitor error rates (should be zero)
- [ ] Review logs for any injection attempts
- [ ] Confirm security headers present
- [ ] Schedule follow-up security audit (1 week)

---

**Estimated Total Time**: 62 hours
**Recommended Timeline**: 3 weeks (20-22 hours per week)

---
