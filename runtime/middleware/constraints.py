"""
Middleware de contraintes et validation des sorties
Guardrails avec regex, JSONSchema, et blocklist
"""

from __future__ import annotations

import re
import json
from typing import Dict, List, Optional, Union
from jsonschema import validate, ValidationError

# Type aliases for strict typing
JsonPrimitive = Union[str, int, float, bool, None]
JsonValue = Union[JsonPrimitive, List["JsonValue"], Dict[str, "JsonValue"]]
JsonSchemaType = Dict[str, JsonValue]


class Guardrail:
    """Guardrail pour valider/blocker des sorties"""

    def __init__(
        self,
        name: str,
        pattern: Optional[str] = None,
        schema: Optional[JsonSchemaType] = None,
        blocklist: Optional[List[str]] = None,
        allowedlist: Optional[List[str]] = None,
    ) -> None:
        """
        Creer un guardrail

        Args:
            name: Nom du guardrail
            pattern: Regex pattern (optionnel)
            schema: JSONSchema (optionnel)
            blocklist: Liste de mots-cles interdits
            allowedlist: Liste de valeurs autorisees
        """
        self.name = name
        self.pattern = pattern
        self.schema = schema
        self.blocklist = blocklist or []
        self.allowedlist = allowedlist or []

    def validate(self, text: str) -> tuple[bool, Optional[str]]:
        """
        Valider un texte selon le guardrail

        Returns:
            (is_valid, error_message)
        """
        # Verifier blocklist
        for blockword in self.blocklist:
            if blockword.lower() in text.lower():
                return False, f"Blocked keyword detected: {blockword}"

        # Verifier allowedlist
        if self.allowedlist:
            # Check if text contains at least one allowed value
            text_lower = text.lower().strip()
            found_allowed = False
            for allowed_value in self.allowedlist:
                if allowed_value.lower() == text_lower or allowed_value.lower() in text_lower:
                    found_allowed = True
                    break
            if not found_allowed:
                return (
                    False,
                    f"Value not in allowedlist. Allowed values: {', '.join(self.allowedlist)}",
                )

        # Verifier regex
        if self.pattern:
            if not re.search(self.pattern, text):
                return False, f"Pattern validation failed for {self.name}"

        # Verifier JSONSchema
        if self.schema:
            try:
                # Essayer de parser JSON
                data = json.loads(text)
                validate(data, self.schema)
            except json.JSONDecodeError:
                return False, "Invalid JSON format"
            except ValidationError as e:
                return False, f"JSONSchema validation failed: {e.message}"

        return True, None


class ConstraintsEngine:
    """
    Engine de contraintes pour validation des sorties
    Applique les guardrails selon config/policies.yaml
    """

    def __init__(self, config_path: str = "config/policies.yaml") -> None:
        self.config_path = config_path
        self.guardrails: List[Guardrail] = []
        self._load_guardrails()

    def _load_guardrails(self) -> None:
        """Charger les guardrails depuis la configuration"""
        import yaml
        from pathlib import Path

        if not Path(self.config_path).exists():
            return

        with open(self.config_path, "r") as f:
            config = yaml.safe_load(f)

        policies: Dict[str, JsonValue] = config.get("policies", {})
        if not isinstance(policies, dict):
            return

        guardrails_config = policies.get("guardrails", {})
        if not isinstance(guardrails_config, dict):
            return

        if not guardrails_config.get("enabled", True):
            return

        # Creer un guardrail pour les blocklist_keywords
        blocklist_keywords = guardrails_config.get("blocklist_keywords")
        if blocklist_keywords and isinstance(blocklist_keywords, list):
            # Ensure all items are strings
            str_blocklist: List[str] = [str(kw) for kw in blocklist_keywords]
            self.guardrails.append(Guardrail(name="keyword_blocklist", blocklist=str_blocklist))

        # Creer un guardrail pour max_length
        max_prompt = guardrails_config.get("max_prompt_length")
        max_response = guardrails_config.get("max_response_length")

        if max_prompt and isinstance(max_prompt, int):
            self.guardrails.append(
                Guardrail(name="max_prompt_length", pattern=rf".{{0,{max_prompt}}}")
            )

        if max_response and isinstance(max_response, int):
            self.guardrails.append(
                Guardrail(name="max_response_length", pattern=rf".{{0,{max_response}}}")
            )

    def validate_output(self, text: str) -> tuple[bool, List[str]]:
        """
        Valider une sortie selon tous les guardrails

        Args:
            text: Texte a valider

        Returns:
            (is_valid, list_of_errors)
        """
        errors: List[str] = []

        for guardrail in self.guardrails:
            is_valid, error = guardrail.validate(text)
            if not is_valid and error:
                errors.append(f"[{guardrail.name}] {error}")

        return len(errors) == 0, errors

    def add_guardrail(self, guardrail: Guardrail) -> None:
        """Ajouter un guardrail personnalise"""
        self.guardrails.append(guardrail)

    def validate_json_output(self, text: str, schema: JsonSchemaType) -> tuple[bool, Optional[str]]:
        """
        Valider une sortie JSON selon un schema

        Args:
            text: JSON text
            schema: JSONSchema

        Returns:
            (is_valid, error_message)
        """
        try:
            data = json.loads(text)
            validate(data, schema)
            return True, None
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"
        except ValidationError as e:
            return False, f"Schema validation failed: {e.message}"


# Instance globale
_constraints_engine: Optional[ConstraintsEngine] = None


def get_constraints_engine() -> ConstraintsEngine:
    """Recuperer l'instance globale"""
    global _constraints_engine
    if _constraints_engine is None:
        _constraints_engine = ConstraintsEngine()
    return _constraints_engine


def init_constraints_engine(config_path: str = "config/policies.yaml") -> ConstraintsEngine:
    """Initialiser le moteur de contraintes"""
    global _constraints_engine
    _constraints_engine = ConstraintsEngine(config_path)
    return _constraints_engine
