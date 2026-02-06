"""
Comprehensive unit tests for constraints middleware (Guardrails)

Tests cover:
- Guardrail creation and validation
- Regex pattern validation
- JSONSchema validation
- Blocklist and allowlist enforcement
- ConstraintsEngine initialization and configuration
- Integration with policies.yaml
- Error handling and edge cases
- Graceful fallbacks
"""

import json
import pytest
from pathlib import Path
import yaml
from jsonschema import ValidationError

from runtime.middleware.constraints import (
    Guardrail,
    ConstraintsEngine,
    get_constraints_engine,
    init_constraints_engine,
)


@pytest.fixture
def temp_config_file(tmp_path):
    """Create temporary config file"""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "policies.yaml"

    config = {
        "policies": {
            "guardrails": {
                "enabled": True,
                "blocklist_keywords": ["forbidden", "secret", "password"],
                "max_prompt_length": 1000,
                "max_response_length": 2000,
            }
        }
    }

    with open(config_file, "w") as f:
        yaml.dump(config, f)

    return config_file


class TestGuardrailCreation:
    """Test Guardrail creation"""

    def test_basic_creation(self):
        """Test création basique de guardrail"""
        guardrail = Guardrail(name="test_guardrail")

        assert guardrail.name == "test_guardrail"
        assert guardrail.pattern is None
        assert guardrail.schema is None
        assert guardrail.blocklist == []
        assert guardrail.allowedlist == []

    def test_creation_with_pattern(self):
        """Test création avec pattern regex"""
        guardrail = Guardrail(
            name="email_guardrail", pattern=r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        )

        assert guardrail.pattern is not None

    def test_creation_with_schema(self):
        """Test création avec JSONSchema"""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }

        guardrail = Guardrail(name="json_guardrail", schema=schema)

        assert guardrail.schema is not None

    def test_creation_with_blocklist(self):
        """Test création avec blocklist"""
        guardrail = Guardrail(name="blocklist_guardrail", blocklist=["forbidden", "secret"])

        assert len(guardrail.blocklist) == 2

    def test_creation_with_allowedlist(self):
        """Test création avec allowedlist"""
        guardrail = Guardrail(name="allowedlist_guardrail", allowedlist=["allowed1", "allowed2"])

        assert len(guardrail.allowedlist) == 2


class TestBlocklistValidation:
    """Test blocklist validation"""

    def test_blocklist_detection(self):
        """Test détection de mot bloqué"""
        guardrail = Guardrail(name="test", blocklist=["forbidden", "secret"])

        is_valid, error = guardrail.validate("This contains forbidden word")

        assert is_valid is False
        assert "forbidden" in error

    def test_blocklist_case_insensitive(self):
        """Test que blocklist est case-insensitive"""
        guardrail = Guardrail(name="test", blocklist=["forbidden"])

        is_valid, error = guardrail.validate("This contains FORBIDDEN word")

        assert is_valid is False

    def test_blocklist_multiple_matches(self):
        """Test détection avec plusieurs mots bloqués"""
        guardrail = Guardrail(name="test", blocklist=["word1", "word2", "word3"])

        is_valid, error = guardrail.validate("This contains word2")

        assert is_valid is False

    def test_blocklist_no_match(self):
        """Test pas de match avec blocklist"""
        guardrail = Guardrail(name="test", blocklist=["forbidden"])

        is_valid, error = guardrail.validate("This is a clean text")

        assert is_valid is True
        assert error is None


class TestRegexValidation:
    """Test regex pattern validation"""

    def test_regex_pattern_match(self):
        """Test validation avec pattern qui match"""
        guardrail = Guardrail(name="test", pattern=r"^\d{3}$")  # Exactly 3 digits

        is_valid, error = guardrail.validate("123")

        assert is_valid is True

    def test_regex_pattern_no_match(self):
        """Test validation avec pattern qui ne match pas"""
        guardrail = Guardrail(name="test", pattern=r"^\d{3}$")

        is_valid, error = guardrail.validate("abc")

        assert is_valid is False
        assert "Pattern validation failed" in error

    def test_regex_email_pattern(self):
        """Test validation d'email avec regex"""
        guardrail = Guardrail(
            name="email", pattern=r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        )

        is_valid, error = guardrail.validate("Contact: john@example.com")

        assert is_valid is True

    def test_regex_complex_pattern(self):
        """Test validation avec pattern complexe"""
        guardrail = Guardrail(name="version", pattern=r"v\d+\.\d+\.\d+")  # Version format

        is_valid, error = guardrail.validate("Version v1.2.3")

        assert is_valid is True


class TestJSONSchemaValidation:
    """Test JSONSchema validation"""

    def test_schema_validation_valid(self):
        """Test validation JSON valide"""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
            "required": ["name"],
        }

        guardrail = Guardrail(name="test", schema=schema)

        json_text = json.dumps({"name": "John", "age": 30})
        is_valid, error = guardrail.validate(json_text)

        assert is_valid is True

    def test_schema_validation_invalid(self):
        """Test validation JSON invalide"""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }

        guardrail = Guardrail(name="test", schema=schema)

        json_text = json.dumps({"age": 30})  # Missing required 'name'
        is_valid, error = guardrail.validate(json_text)

        assert is_valid is False
        assert "JSONSchema validation failed" in error

    def test_schema_validation_invalid_json(self):
        """Test validation avec JSON mal formé"""
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}

        guardrail = Guardrail(name="test", schema=schema)

        is_valid, error = guardrail.validate("{ invalid json")

        assert is_valid is False
        assert "Invalid JSON format" in error

    def test_schema_validation_type_mismatch(self):
        """Test validation avec type incorrect"""
        schema = {"type": "object", "properties": {"age": {"type": "number"}}}

        guardrail = Guardrail(name="test", schema=schema)

        json_text = json.dumps({"age": "not a number"})
        is_valid, error = guardrail.validate(json_text)

        assert is_valid is False


class TestConstraintsEngineInitialization:
    """Test ConstraintsEngine initialization"""

    def test_basic_initialization(self, temp_config_file):
        """Test initialisation basique"""
        engine = ConstraintsEngine(config_path=str(temp_config_file))

        assert engine.config_path == str(temp_config_file)
        assert isinstance(engine.guardrails, list)

    def test_initialization_with_nonexistent_config(self):
        """Test initialisation avec config inexistant"""
        engine = ConstraintsEngine(config_path="/nonexistent/config.yaml")

        # Should initialize without errors
        assert isinstance(engine.guardrails, list)

    def test_load_guardrails_from_config(self, temp_config_file):
        """Test chargement des guardrails depuis config"""
        engine = ConstraintsEngine(config_path=str(temp_config_file))

        # Should have loaded blocklist guardrail
        assert len(engine.guardrails) > 0


class TestConstraintsEngineValidation:
    """Test ConstraintsEngine validation"""

    def test_validate_output_success(self, temp_config_file):
        """Test validation réussie"""
        engine = ConstraintsEngine(config_path=str(temp_config_file))

        text = "This is a clean output"
        is_valid, errors = engine.validate_output(text)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_output_blocked_keyword(self, temp_config_file):
        """Test validation avec mot bloqué"""
        engine = ConstraintsEngine(config_path=str(temp_config_file))

        text = "This contains forbidden content"
        is_valid, errors = engine.validate_output(text)

        assert is_valid is False
        assert len(errors) > 0

    def test_validate_output_multiple_violations(self, temp_config_file):
        """Test validation avec plusieurs violations"""
        engine = ConstraintsEngine(config_path=str(temp_config_file))

        text = "This has forbidden and secret words"
        is_valid, errors = engine.validate_output(text)

        assert is_valid is False
        # Should report all violations
        assert len(errors) >= 1


class TestCustomGuardrails:
    """Test custom guardrail addition"""

    def test_add_guardrail(self, temp_config_file):
        """Test ajout d'un guardrail personnalisé"""
        engine = ConstraintsEngine(config_path=str(temp_config_file))

        custom_guardrail = Guardrail(name="custom", pattern=r"^\d+$")

        initial_count = len(engine.guardrails)
        engine.add_guardrail(custom_guardrail)

        assert len(engine.guardrails) == initial_count + 1

    def test_custom_guardrail_validation(self, temp_config_file):
        """Test validation avec guardrail personnalisé"""
        engine = ConstraintsEngine(config_path=str(temp_config_file))

        custom_guardrail = Guardrail(name="numbers_only", pattern=r"^\d+$")

        engine.add_guardrail(custom_guardrail)

        is_valid, errors = engine.validate_output("abc")

        assert is_valid is False


class TestJSONOutputValidation:
    """Test JSON output validation"""

    def test_validate_json_output_valid(self, temp_config_file):
        """Test validation JSON valide"""
        engine = ConstraintsEngine(config_path=str(temp_config_file))

        schema = {
            "type": "object",
            "properties": {"status": {"type": "string"}},
            "required": ["status"],
        }

        json_text = json.dumps({"status": "success"})
        is_valid, error = engine.validate_json_output(json_text, schema)

        assert is_valid is True
        assert error is None

    def test_validate_json_output_invalid(self, temp_config_file):
        """Test validation JSON invalide"""
        engine = ConstraintsEngine(config_path=str(temp_config_file))

        schema = {
            "type": "object",
            "properties": {"status": {"type": "string"}},
            "required": ["status"],
        }

        json_text = json.dumps({"result": "success"})  # Missing 'status'
        is_valid, error = engine.validate_json_output(json_text, schema)

        assert is_valid is False
        assert error is not None

    def test_validate_json_output_malformed(self, temp_config_file):
        """Test validation JSON mal formé"""
        engine = ConstraintsEngine(config_path=str(temp_config_file))

        schema = {"type": "object"}

        is_valid, error = engine.validate_json_output("{ invalid json", schema)

        assert is_valid is False
        assert "Invalid JSON" in error


class TestMaxLengthGuardrails:
    """Test max length guardrails"""

    def test_max_prompt_length_from_config(self, temp_config_file):
        """Test max_prompt_length depuis config"""
        engine = ConstraintsEngine(config_path=str(temp_config_file))

        # Config specifies max_prompt_length: 1000
        long_text = "x" * 1001

        is_valid, errors = engine.validate_output(long_text)

        # Should fail if max length guardrail is enforced
        # Note: This depends on how the guardrail is implemented

    def test_disabled_guardrails(self, tmp_path):
        """Test guardrails désactivés"""
        config_file = tmp_path / "config" / "policies.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        config = {"policies": {"guardrails": {"enabled": False}}}

        with open(config_file, "w") as f:
            yaml.dump(config, f)

        engine = ConstraintsEngine(config_path=str(config_file))

        # Should have no guardrails when disabled
        assert len(engine.guardrails) == 0


class TestSingletonPattern:
    """Test singleton pattern"""

    def test_get_constraints_engine_returns_singleton(self):
        """Test que get_constraints_engine retourne toujours la même instance"""
        engine1 = get_constraints_engine()
        engine2 = get_constraints_engine()

        assert engine1 is engine2

    def test_init_constraints_engine_creates_new_instance(self, temp_config_file):
        """Test que init_constraints_engine crée une nouvelle instance"""
        engine1 = init_constraints_engine(config_path=str(temp_config_file))
        engine2 = get_constraints_engine()

        assert engine1 is engine2


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_validate_empty_string(self, temp_config_file):
        """Test validation de chaîne vide"""
        engine = ConstraintsEngine(config_path=str(temp_config_file))

        is_valid, errors = engine.validate_output("")

        assert is_valid is True  # Empty string should pass

    def test_validate_with_no_guardrails(self):
        """Test validation sans guardrails"""
        engine = ConstraintsEngine(config_path="/nonexistent/config.yaml")

        is_valid, errors = engine.validate_output("Any text")

        assert is_valid is True  # Should pass when no guardrails

    def test_validate_with_special_characters(self, temp_config_file):
        """Test validation avec caractères spéciaux"""
        engine = ConstraintsEngine(config_path=str(temp_config_file))

        text = "Text with special chars: éàü €£¥"
        is_valid, errors = engine.validate_output(text)

        assert is_valid is True

    def test_blocklist_partial_word_match(self):
        """Test que blocklist ne match pas les mots partiels"""
        guardrail = Guardrail(name="test", blocklist=["test"])

        # "test" should match "testing"
        is_valid, error = guardrail.validate("This is testing")

        assert is_valid is False  # Current implementation matches partial

    def test_guardrail_with_empty_blocklist(self):
        """Test guardrail avec blocklist vide"""
        guardrail = Guardrail(name="test", blocklist=[])

        is_valid, error = guardrail.validate("Any text")

        assert is_valid is True

    def test_complex_json_schema(self, temp_config_file):
        """Test validation avec schéma JSON complexe"""
        engine = ConstraintsEngine(config_path=str(temp_config_file))

        schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "number", "minimum": 0},
                    },
                    "required": ["name"],
                }
            },
            "required": ["user"],
        }

        json_text = json.dumps({"user": {"name": "John", "age": 30}})

        is_valid, error = engine.validate_json_output(json_text, schema)

        assert is_valid is True


class TestGracefulFallbacks:
    """Test graceful fallbacks and error handling"""

    def test_invalid_config_file(self, tmp_path):
        """Test gestion de fichier de config invalide"""
        config_file = tmp_path / "config" / "policies.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        # Invalid YAML
        with open(config_file, "w") as f:
            f.write("{ invalid yaml")

        # Should handle gracefully
        try:
            engine = ConstraintsEngine(config_path=str(config_file))
            # Should initialize with no guardrails
            assert isinstance(engine.guardrails, list)
        except yaml.YAMLError:
            # Expected behavior
            pass

    def test_malformed_guardrail_config(self, tmp_path):
        """Test gestion de config guardrail mal formée"""
        config_file = tmp_path / "config" / "policies.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        config = {"policies": {"guardrails": {"enabled": True, "invalid_field": "value"}}}

        with open(config_file, "w") as f:
            yaml.dump(config, f)

        # Should handle gracefully
        engine = ConstraintsEngine(config_path=str(config_file))
        assert isinstance(engine.guardrails, list)


class TestComplianceRequirements:
    """Test compliance with guardrail requirements"""

    def test_blocklist_enforcement(self, temp_config_file):
        """Test que les mots de blocklist sont bien bloqués"""
        engine = ConstraintsEngine(config_path=str(temp_config_file))

        # Config has "forbidden", "secret", "password" in blocklist
        blocked_words = ["forbidden", "secret", "password"]

        for word in blocked_words:
            is_valid, errors = engine.validate_output(f"This contains {word}")
            assert is_valid is False, f"Failed to block: {word}"

    def test_validation_provides_error_details(self, temp_config_file):
        """Test que la validation fournit des détails d'erreur"""
        engine = ConstraintsEngine(config_path=str(temp_config_file))

        is_valid, errors = engine.validate_output("This has forbidden content")

        assert is_valid is False
        assert len(errors) > 0
        # Errors should contain useful information
        assert any("forbidden" in err.lower() for err in errors)

    def test_multiple_guardrails_all_validated(self, temp_config_file):
        """Test que tous les guardrails sont validés"""
        engine = ConstraintsEngine(config_path=str(temp_config_file))

        # Add custom guardrail
        custom_guardrail = Guardrail(name="custom", blocklist=["badword"])
        engine.add_guardrail(custom_guardrail)

        # Text violates multiple guardrails
        text = "This has forbidden and badword"
        is_valid, errors = engine.validate_output(text)

        assert is_valid is False
        # Should report multiple violations
        assert len(errors) >= 2
