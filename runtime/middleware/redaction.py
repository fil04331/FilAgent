"""
Middleware de redaction PII (Personally Identifiable Information)
Masquage automatique des données sensibles selon config/policies.yaml
"""

import re
from typing import Dict, List, Optional
from pathlib import Path
import yaml


class PIIDetector:
    """Détecteur de PII avec patterns regex"""

    PATTERNS = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
        "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "mac_address": r"\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b",
    }

    def __init__(self, fields_to_mask: Optional[List[str]] = None):
        """
        Créer un détecteur PII

        Args:
            fields_to_mask: Liste des types de PII à masquer
        """
        self.fields_to_mask = fields_to_mask or list(self.PATTERNS.keys())

    def detect(self, text: str) -> List[Dict[str, str]]:
        """
        Détecter toutes les PII dans un texte

        Returns:
            Liste de dicts avec 'type', 'value', 'start', 'end'
        """
        detected = []

        for pii_type in self.fields_to_mask:
            if pii_type not in self.PATTERNS:
                continue

            pattern = self.PATTERNS[pii_type]
            for match in re.finditer(pattern, text):
                detected.append({"type": pii_type, "value": match.group(), "start": match.start(), "end": match.end()})

        return detected

    def redact(self, text: str, replacement: str = "[REDACTED]") -> str:
        """
        Redacter toutes les PII d'un texte

        Args:
            text: Texte à redacter
            replacement: Texte de remplacement (default: [REDACTED])

        Returns:
            Texte avec PII redactées
        """
        detected = self.detect(text)

        # Trier par position pour redacter de droite à gauche
        detected.sort(key=lambda x: x["start"], reverse=True)

        redacted_text = text
        for pii in detected:
            redacted_text = redacted_text[:pii["start"]] + replacement + redacted_text[pii["end"]:]

        return redacted_text

    def is_pii_present(self, text: str) -> bool:
        """Vérifier si du PII est présent"""
        return len(self.detect(text)) > 0


class PIIRedactor:
    """
    Redacteur PII avec configuration et logging
    """

    def __init__(self, config_path: str = "config/policies.yaml"):
        self.config_path = Path(config_path)
        self.enabled = True
        self.replacement_pattern = "[REDACTED]"
        self.fields_to_mask = []
        self.scan_before_logging = True

        self._load_config()
        self.detector = PIIDetector(self.fields_to_mask)

    def _load_config(self):
        """Charger la configuration depuis policies.yaml"""
        if not self.config_path.exists():
            return

        with open(self.config_path, "r") as f:
            config = yaml.safe_load(f)

        policies = config.get("policies", {})
        pii_config = policies.get("pii", {})

        self.enabled = pii_config.get("enabled", True)
        self.replacement_pattern = pii_config.get("replacement_pattern", "[REDACTED]")
        self.fields_to_mask = pii_config.get("fields_to_mask", [])
        self.scan_before_logging = pii_config.get("scan_before_logging", True)

    def redact(self, text: str) -> str:
        """
        Redacter un texte selon la configuration

        Returns:
            Texte avec PII redactées
        """
        if not self.enabled:
            return text

        return self.detector.redact(text, self.replacement_pattern)

    def scan_and_log(self, text: str, context: Optional[Dict] = None) -> Dict:
        """
        Scanner un texte pour PII et logger si trouvé

        Args:
            text: Texte à scanner
            context: Contexte additionnel

        Returns:
            Dict avec 'has_pii', 'pii_count', 'types_found'
        """
        if not self.scan_before_logging:
            return {"has_pii": False, "pii_count": 0, "types_found": []}

        detected = self.detector.detect(text)
        pii_types = set([pii["type"] for pii in detected])

        result = {
            "has_pii": len(detected) > 0,
            "pii_count": len(detected),
            "types_found": list(pii_types),
            "detected": detected,
        }

        # Logger si PII trouvé
        if result["has_pii"]:
            try:
                from runtime.middleware.logging import get_logger

                logger = get_logger()
                logger.log_event(
                    actor="pii.redactor",
                    event="pii.detected",
                    level="WARNING",
                    metadata={"pii_count": len(detected), "pii_types": list(pii_types), "context": context},
                )
            except Exception:
                # Graceful fallback if logger is unavailable
                pass

        return result


# Instance globale
_pii_redactor: Optional[PIIRedactor] = None


def get_pii_redactor() -> PIIRedactor:
    """Récupérer l'instance globale"""
    global _pii_redactor
    if _pii_redactor is None:
        _pii_redactor = PIIRedactor()
    return _pii_redactor


def init_pii_redactor(config_path: str = "config/policies.yaml") -> PIIRedactor:
    """Initialiser le redacteur PII"""
    global _pii_redactor
    _pii_redactor = PIIRedactor(config_path)
    return _pii_redactor


def reset_pii_redactor():
    """Reset the global PII redactor instance (primarily for testing)"""
    global _pii_redactor
    _pii_redactor = None
