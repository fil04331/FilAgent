"""
Middleware de contraintes et validation des sorties
Guardrails avec regex, JSONSchema, et blocklist
"""
import re
import json
from typing import Dict, Any, Optional, List
from jsonschema import validate, ValidationError
from datetime import datetime


class Guardrail:
    """Guardrail pour valider/blocker des sorties"""
    
    def __init__(
        self,
        name: str,
        pattern: Optional[str] = None,
        schema: Optional[Dict] = None,
        blocklist: Optional[List[str]] = None,
        allowedlist: Optional[List[str]] = None
    ):
        """
        Créer un guardrail
        
        Args:
            name: Nom du guardrail
            pattern: Regex pattern (optionnel)
            schema: JSONSchema (optionnel)
            blocklist: Liste de mots-clés interdits
            allowedlist: Liste de valeurs autorisées
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
        # Vérifier blocklist
        for blockword in self.blocklist:
            if blockword.lower() in text.lower():
                return False, f"Blocked keyword detected: {blockword}"
        
        # Vérifier allowedlist
        if self.allowedlist:
            # TODO: Implémentation plus sophistiquée selon le cas d'usage
            pass
        
        # Vérifier regex
        if self.pattern:
            if not re.search(self.pattern, text):
                return False, f"Pattern validation failed for {self.name}"
        
        # Vérifier JSONSchema
        if self.schema:
            try:
                # Essayer de parser JSON
                data = json.loads(text)
                validate(data, self.schema)
            except json.JSONDecodeError:
                return False, f"Invalid JSON format"
            except ValidationError as e:
                return False, f"JSONSchema validation failed: {e.message}"
        
        return True, None


class ConstraintsEngine:
    """
    Engine de contraintes pour validation des sorties
    Applique les guardrails selon config/policies.yaml
    """
    
    def __init__(self, config_path: str = "config/policies.yaml"):
        self.config_path = config_path
        self.guardrails: List[Guardrail] = []
        self._load_guardrails()
    
    def _load_guardrails(self):
        """Charger les guardrails depuis la configuration"""
        import yaml
        from pathlib import Path
        
        if not Path(self.config_path).exists():
            return
        
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        policies = config.get('policies', {})
        guardrails_config = policies.get('guardrails', {})
        
        if not guardrails_config.get('enabled', True):
            return
        
        # Créer un guardrail pour les blocklist_keywords
        if guardrails_config.get('blocklist_keywords'):
            self.guardrails.append(Guardrail(
                name="keyword_blocklist",
                blocklist=guardrails_config['blocklist_keywords']
            ))
        
        # Créer un guardrail pour max_length
        max_prompt = guardrails_config.get('max_prompt_length')
        max_response = guardrails_config.get('max_response_length')
        
        if max_prompt:
            self.guardrails.append(Guardrail(
                name="max_prompt_length",
                pattern=rf".{{0,{max_prompt}}}"
            ))
        
        if max_response:
            self.guardrails.append(Guardrail(
                name="max_response_length",
                pattern=rf".{{0,{max_response}}}"
            ))
    
    def validate_output(self, text: str) -> tuple[bool, List[str]]:
        """
        Valider une sortie selon tous les guardrails
        
        Args:
            text: Texte à valider
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        for guardrail in self.guardrails:
            is_valid, error = guardrail.validate(text)
            if not is_valid:
                errors.append(f"[{guardrail.name}] {error}")
        
        return len(errors) == 0, errors
    
    def add_guardrail(self, guardrail: Guardrail):
        """Ajouter un guardrail personnalisé"""
        self.guardrails.append(guardrail)
    
    def validate_json_output(self, text: str, schema: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Valider une sortie JSON selon un schéma
        
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
    """Récupérer l'instance globale"""
    global _constraints_engine
    if _constraints_engine is None:
        _constraints_engine = ConstraintsEngine()
    return _constraints_engine


def init_constraints_engine(config_path: str = "config/policies.yaml") -> ConstraintsEngine:
    """Initialiser le moteur de contraintes"""
    global _constraints_engine
    _constraints_engine = ConstraintsEngine(config_path)
    return _constraints_engine
