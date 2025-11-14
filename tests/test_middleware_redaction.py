"""
Comprehensive unit tests for redaction middleware (PII masking)

Tests cover:
- PIIDetector initialization and pattern matching
- PII detection for various types (email, phone, SSN, etc.)
- PII redaction functionality
- PIIRedactor configuration loading
- Integration with logging middleware
- Graceful fallbacks and error handling
- Edge cases and special characters
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import yaml

from runtime.middleware.redaction import (
    PIIDetector,
    PIIRedactor,
    get_pii_redactor,
    init_pii_redactor,
    reset_pii_redactor
)


@pytest.fixture(autouse=True)
def cleanup_redactor():
    """Reset global redactor before and after each test"""
    reset_pii_redactor()
    yield
    reset_pii_redactor()


@pytest.fixture
def temp_config_file(tmp_path):
    """Create temporary config file"""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "policies.yaml"

    config = {
        "policies": {
            "pii": {
                "enabled": True,
                "replacement_pattern": "[REDACTED]",
                "fields_to_mask": ["email", "phone", "ssn"],
                "scan_before_logging": True
            }
        }
    }

    with open(config_file, 'w') as f:
        yaml.dump(config, f)

    return config_file


class TestPIIDetectorInitialization:
    """Test PIIDetector initialization"""

    def test_basic_initialization(self):
        """Test initialisation basique"""
        detector = PIIDetector()

        assert detector.fields_to_mask is not None
        assert len(detector.fields_to_mask) > 0

    def test_initialization_with_specific_fields(self):
        """Test initialisation avec champs spécifiques"""
        detector = PIIDetector(fields_to_mask=["email", "phone"])

        assert len(detector.fields_to_mask) == 2
        assert "email" in detector.fields_to_mask
        assert "phone" in detector.fields_to_mask

    def test_default_patterns(self):
        """Test patterns par défaut"""
        detector = PIIDetector()

        expected_patterns = ["email", "phone", "ssn", "credit_card", "ip_address", "mac_address"]
        for pattern in expected_patterns:
            assert pattern in PIIDetector.PATTERNS


class TestEmailDetection:
    """Test email detection"""

    def test_detect_single_email(self):
        """Test détection d'un seul email"""
        detector = PIIDetector(fields_to_mask=["email"])

        text = "Contact me at john@example.com"
        detected = detector.detect(text)

        assert len(detected) == 1
        assert detected[0]["type"] == "email"
        assert detected[0]["value"] == "john@example.com"

    def test_detect_multiple_emails(self):
        """Test détection de plusieurs emails"""
        detector = PIIDetector(fields_to_mask=["email"])

        text = "Contact john@example.com or jane@example.org"
        detected = detector.detect(text)

        assert len(detected) == 2

    def test_detect_email_with_numbers(self):
        """Test détection d'email avec chiffres"""
        detector = PIIDetector(fields_to_mask=["email"])

        text = "Email: user123@example.com"
        detected = detector.detect(text)

        assert len(detected) == 1
        assert detected[0]["value"] == "user123@example.com"

    def test_redact_email(self):
        """Test redaction d'email"""
        detector = PIIDetector(fields_to_mask=["email"])

        text = "Contact me at john@example.com"
        redacted = detector.redact(text)

        assert "john@example.com" not in redacted
        assert "[REDACTED]" in redacted


class TestPhoneDetection:
    """Test phone number detection"""

    def test_detect_phone_basic(self):
        """Test détection de numéro de téléphone basique"""
        detector = PIIDetector(fields_to_mask=["phone"])

        text = "Call me at 555-123-4567"
        detected = detector.detect(text)

        assert len(detected) == 1
        assert detected[0]["type"] == "phone"

    def test_detect_phone_with_parentheses(self):
        """Test détection de numéro avec parenthèses"""
        detector = PIIDetector(fields_to_mask=["phone"])

        text = "Phone: (555) 123-4567"
        detected = detector.detect(text)

        assert len(detected) == 1

    def test_detect_phone_with_spaces(self):
        """Test détection de numéro avec espaces"""
        detector = PIIDetector(fields_to_mask=["phone"])

        text = "Number: 555 123 4567"
        detected = detector.detect(text)

        assert len(detected) == 1

    def test_redact_phone(self):
        """Test redaction de numéro de téléphone"""
        detector = PIIDetector(fields_to_mask=["phone"])

        text = "Call me at 555-123-4567"
        redacted = detector.redact(text)

        assert "555-123-4567" not in redacted
        assert "[REDACTED]" in redacted


class TestSSNDetection:
    """Test SSN detection"""

    def test_detect_ssn(self):
        """Test détection de SSN"""
        detector = PIIDetector(fields_to_mask=["ssn"])

        text = "SSN: 123-45-6789"
        detected = detector.detect(text)

        assert len(detected) == 1
        assert detected[0]["type"] == "ssn"
        assert detected[0]["value"] == "123-45-6789"

    def test_redact_ssn(self):
        """Test redaction de SSN"""
        detector = PIIDetector(fields_to_mask=["ssn"])

        text = "SSN: 123-45-6789"
        redacted = detector.redact(text)

        assert "123-45-6789" not in redacted
        assert "[REDACTED]" in redacted


class TestCreditCardDetection:
    """Test credit card detection"""

    def test_detect_credit_card(self):
        """Test détection de carte de crédit"""
        detector = PIIDetector(fields_to_mask=["credit_card"])

        text = "Card: 4111-1111-1111-1111"
        detected = detector.detect(text)

        assert len(detected) == 1
        assert detected[0]["type"] == "credit_card"

    def test_detect_credit_card_no_dashes(self):
        """Test détection de carte sans tirets"""
        detector = PIIDetector(fields_to_mask=["credit_card"])

        text = "Card: 4111111111111111"
        detected = detector.detect(text)

        assert len(detected) == 1


class TestIPAddressDetection:
    """Test IP address detection"""

    def test_detect_ip_address(self):
        """Test détection d'adresse IP"""
        detector = PIIDetector(fields_to_mask=["ip_address"])

        text = "IP: 192.168.1.1"
        detected = detector.detect(text)

        assert len(detected) == 1
        assert detected[0]["type"] == "ip_address"
        assert detected[0]["value"] == "192.168.1.1"

    def test_redact_ip_address(self):
        """Test redaction d'adresse IP"""
        detector = PIIDetector(fields_to_mask=["ip_address"])

        text = "Server IP: 192.168.1.1"
        redacted = detector.redact(text)

        assert "192.168.1.1" not in redacted
        assert "[REDACTED]" in redacted


class TestMACAddressDetection:
    """Test MAC address detection"""

    def test_detect_mac_address_colon(self):
        """Test détection de MAC address avec ':'"""
        detector = PIIDetector(fields_to_mask=["mac_address"])

        text = "MAC: 00:1A:2B:3C:4D:5E"
        detected = detector.detect(text)

        assert len(detected) == 1
        assert detected[0]["type"] == "mac_address"

    def test_detect_mac_address_dash(self):
        """Test détection de MAC address avec '-'"""
        detector = PIIDetector(fields_to_mask=["mac_address"])

        text = "MAC: 00-1A-2B-3C-4D-5E"
        detected = detector.detect(text)

        assert len(detected) == 1


class TestMultipleDetection:
    """Test detection of multiple PII types"""

    def test_detect_multiple_types(self):
        """Test détection de plusieurs types de PII"""
        detector = PIIDetector()

        text = "Contact john@example.com or call 555-123-4567"
        detected = detector.detect(text)

        assert len(detected) == 2
        types = [d["type"] for d in detected]
        assert "email" in types
        assert "phone" in types

    def test_redact_multiple_types(self):
        """Test redaction de plusieurs types"""
        detector = PIIDetector()

        text = "Email: john@example.com, Phone: 555-123-4567"
        redacted = detector.redact(text)

        assert "john@example.com" not in redacted
        assert "555-123-4567" not in redacted
        assert redacted.count("[REDACTED]") == 2


class TestRedactionOrdering:
    """Test redaction ordering and position tracking"""

    def test_redaction_preserves_text_structure(self):
        """Test que la redaction préserve la structure du texte"""
        detector = PIIDetector(fields_to_mask=["email"])

        text = "Start john@example.com middle jane@example.com end"
        redacted = detector.redact(text)

        assert "Start" in redacted
        assert "middle" in redacted
        assert "end" in redacted

    def test_is_pii_present(self):
        """Test détection de présence de PII"""
        detector = PIIDetector()

        text_with_pii = "Contact john@example.com"
        text_without_pii = "This is a clean text"

        assert detector.is_pii_present(text_with_pii) is True
        assert detector.is_pii_present(text_without_pii) is False


class TestPIIRedactorInitialization:
    """Test PIIRedactor initialization"""

    def test_basic_initialization(self, temp_config_file):
        """Test initialisation basique"""
        redactor = PIIRedactor(config_path=str(temp_config_file))

        assert redactor.enabled is True
        assert redactor.replacement_pattern == "[REDACTED]"
        assert len(redactor.fields_to_mask) > 0

    def test_initialization_with_nonexistent_config(self):
        """Test initialisation avec config inexistant"""
        redactor = PIIRedactor(config_path="/nonexistent/config.yaml")

        # Should initialize with defaults
        assert redactor.enabled is True

    def test_load_config_from_file(self, temp_config_file):
        """Test chargement de config depuis fichier"""
        redactor = PIIRedactor(config_path=str(temp_config_file))

        assert "email" in redactor.fields_to_mask
        assert "phone" in redactor.fields_to_mask
        assert "ssn" in redactor.fields_to_mask


class TestPIIRedactorRedaction:
    """Test PIIRedactor redaction functionality"""

    def test_redact_when_enabled(self, temp_config_file):
        """Test redaction quand activé"""
        redactor = PIIRedactor(config_path=str(temp_config_file))

        text = "Contact john@example.com"
        redacted = redactor.redact(text)

        assert "john@example.com" not in redacted

    def test_redact_when_disabled(self, tmp_path):
        """Test redaction quand désactivé"""
        config_file = tmp_path / "config" / "policies.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        config = {
            "policies": {
                "pii": {
                    "enabled": False
                }
            }
        }

        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        redactor = PIIRedactor(config_path=str(config_file))

        text = "Contact john@example.com"
        redacted = redactor.redact(text)

        # Should not redact when disabled
        assert redacted == text

    def test_custom_replacement_pattern(self, tmp_path):
        """Test pattern de remplacement personnalisé"""
        config_file = tmp_path / "config" / "policies.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        config = {
            "policies": {
                "pii": {
                    "enabled": True,
                    "replacement_pattern": "[XXX]",
                    "fields_to_mask": ["email"]
                }
            }
        }

        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        redactor = PIIRedactor(config_path=str(config_file))

        text = "Contact john@example.com"
        redacted = redactor.redact(text)

        assert "[XXX]" in redacted
        assert "[REDACTED]" not in redacted


class TestScanAndLog:
    """Test scan_and_log functionality"""

    def test_scan_and_log_with_pii(self, temp_config_file):
        """Test scan avec PII présent"""
        with patch('runtime.middleware.redaction.get_logger') as mock_logger:
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance

            redactor = PIIRedactor(config_path=str(temp_config_file))

            text = "Contact john@example.com"
            result = redactor.scan_and_log(text)

            assert result["has_pii"] is True
            assert result["pii_count"] == 1
            assert "email" in result["types_found"]

            # Should have logged the PII detection
            mock_logger_instance.log_event.assert_called_once()

    def test_scan_and_log_without_pii(self, temp_config_file):
        """Test scan sans PII"""
        redactor = PIIRedactor(config_path=str(temp_config_file))

        text = "This is a clean text"
        result = redactor.scan_and_log(text)

        assert result["has_pii"] is False
        assert result["pii_count"] == 0
        assert len(result["types_found"]) == 0

    def test_scan_and_log_with_context(self, temp_config_file):
        """Test scan avec contexte"""
        with patch('runtime.middleware.redaction.get_logger') as mock_logger:
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance

            redactor = PIIRedactor(config_path=str(temp_config_file))

            text = "Contact john@example.com"
            context = {"field": "user_input"}
            result = redactor.scan_and_log(text, context=context)

            assert result["has_pii"] is True

    def test_scan_disabled(self, tmp_path):
        """Test scan désactivé"""
        config_file = tmp_path / "config" / "policies.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        config = {
            "policies": {
                "pii": {
                    "enabled": True,
                    "scan_before_logging": False,
                    "fields_to_mask": ["email"]
                }
            }
        }

        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        redactor = PIIRedactor(config_path=str(config_file))

        text = "Contact john@example.com"
        result = redactor.scan_and_log(text)

        # Should return no PII when scanning is disabled
        assert result["has_pii"] is False


class TestSingletonPattern:
    """Test singleton pattern"""

    def test_get_pii_redactor_returns_singleton(self):
        """Test que get_pii_redactor retourne toujours la même instance"""
        redactor1 = get_pii_redactor()
        redactor2 = get_pii_redactor()

        assert redactor1 is redactor2

    def test_init_pii_redactor_creates_new_instance(self, temp_config_file):
        """Test que init_pii_redactor crée une nouvelle instance"""
        redactor1 = init_pii_redactor(config_path=str(temp_config_file))
        redactor2 = get_pii_redactor()

        assert redactor1 is redactor2

    def test_reset_pii_redactor_clears_singleton(self):
        """Test que reset_pii_redactor efface le singleton"""
        redactor1 = get_pii_redactor()
        reset_pii_redactor()
        redactor2 = get_pii_redactor()

        assert redactor1 is not redactor2


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_redact_empty_string(self):
        """Test redaction de chaîne vide"""
        detector = PIIDetector()

        text = ""
        redacted = detector.redact(text)

        assert redacted == ""

    def test_redact_no_pii(self):
        """Test redaction sans PII"""
        detector = PIIDetector()

        text = "This is a clean text"
        redacted = detector.redact(text)

        assert redacted == text

    def test_redact_with_special_characters(self):
        """Test redaction avec caractères spéciaux"""
        detector = PIIDetector(fields_to_mask=["email"])

        text = "Email: john@example.com avec accents: éàü"
        redacted = detector.redact(text)

        assert "john@example.com" not in redacted
        assert "éàü" in redacted

    def test_redact_overlapping_patterns(self):
        """Test redaction avec patterns qui se chevauchent"""
        detector = PIIDetector()

        # Some IP addresses might look like part of other patterns
        text = "IP: 192.168.1.1 and 10.0.0.1"
        redacted = detector.redact(text)

        assert "192.168.1.1" not in redacted

    def test_detect_pii_case_insensitive(self):
        """Test que la détection n'est pas sensible à la casse pour le texte"""
        detector = PIIDetector(fields_to_mask=["email"])

        text = "CONTACT JOHN@EXAMPLE.COM"
        detected = detector.detect(text)

        assert len(detected) == 1

    def test_redact_with_custom_replacement(self):
        """Test redaction avec remplacement personnalisé"""
        detector = PIIDetector(fields_to_mask=["email"])

        text = "Contact john@example.com"
        redacted = detector.redact(text, replacement="[EMAIL]")

        assert "[EMAIL]" in redacted
        assert "john@example.com" not in redacted


class TestGracefulFallbacks:
    """Test graceful fallbacks and error handling"""

    def test_logger_failure_graceful(self, temp_config_file):
        """Test gestion gracieuse d'échec du logger"""
        with patch('runtime.middleware.redaction.get_logger', side_effect=Exception("Logger failed")):
            redactor = PIIRedactor(config_path=str(temp_config_file))

            text = "Contact john@example.com"

            # Should not raise exception
            result = redactor.scan_and_log(text)

            # Should still detect PII
            assert result["has_pii"] is True

    def test_invalid_config_file(self, tmp_path):
        """Test gestion de fichier de config invalide"""
        config_file = tmp_path / "config" / "policies.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        # Invalid YAML
        with open(config_file, 'w') as f:
            f.write("{ invalid yaml")

        # Should handle gracefully
        try:
            redactor = PIIRedactor(config_path=str(config_file))
            # Should use defaults
            assert redactor.enabled is True
        except yaml.YAMLError:
            # Expected behavior
            pass


class TestComplianceRequirements:
    """Test compliance with PII protection requirements"""

    def test_all_pii_types_supported(self):
        """Test que tous les types de PII requis sont supportés"""
        detector = PIIDetector()

        required_types = ["email", "phone", "ssn", "credit_card", "ip_address"]
        for pii_type in required_types:
            assert pii_type in PIIDetector.PATTERNS

    def test_redaction_is_irreversible(self):
        """Test que la redaction est irréversible"""
        detector = PIIDetector(fields_to_mask=["email"])

        text = "Contact john@example.com"
        redacted = detector.redact(text)

        # Original PII should not be recoverable
        assert "john@example.com" not in redacted
        assert "@example.com" not in redacted

    def test_pii_logged_before_redaction(self, temp_config_file):
        """Test que la détection de PII est loggée"""
        with patch('runtime.middleware.redaction.get_logger') as mock_logger:
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance

            redactor = PIIRedactor(config_path=str(temp_config_file))

            text = "Contact john@example.com"
            redactor.scan_and_log(text)

            # Should have logged PII detection
            assert mock_logger_instance.log_event.called
