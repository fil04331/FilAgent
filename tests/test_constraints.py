"""
Tests unitaires pour runtime/middleware/constraints.py

Ce module teste:
- Validation JSONSchema
- Validation par regex pattern
- Blocklist et allowedlist
- Gestion des violations de contraintes
- Fonctions de contraintes personnalisées
- ConstraintsEngine
"""

import pytest
import json
import tempfile
from pathlib import Path
from typing import Dict, Any

from runtime.middleware.constraints import (
    Guardrail,
    ConstraintsEngine,
    get_constraints_engine,
    init_constraints_engine,
)

# ============================================================================
# TESTS: Guardrail - JSONSchema Validation
# ============================================================================


@pytest.mark.unit
def test_guardrail_jsonschema_valid():
    """
    Test de validation JSONSchema: données valides

    Vérifie:
    - Validation réussie pour données conformes au schéma
    - Pas d'erreur retournée
    """
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
        "required": ["name", "age"],
    }

    guardrail = Guardrail(name="test_schema", schema=schema)

    valid_json = json.dumps({"name": "Alice", "age": 30})
    is_valid, error = guardrail.validate(valid_json)

    assert is_valid is True
    assert error is None


@pytest.mark.unit
def test_guardrail_jsonschema_invalid_missing_required():
    """
    Test de validation JSONSchema: champ requis manquant

    Vérifie:
    - Détection des champs requis manquants
    - Message d'erreur approprié
    """
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
        "required": ["name", "age"],
    }

    guardrail = Guardrail(name="test_schema", schema=schema)

    # age est manquant
    invalid_json = json.dumps({"name": "Alice"})
    is_valid, error = guardrail.validate(invalid_json)

    assert is_valid is False
    assert error is not None
    assert "JSONSchema validation failed" in error


@pytest.mark.unit
def test_guardrail_jsonschema_invalid_type():
    """
    Test de validation JSONSchema: type incorrect

    Vérifie:
    - Détection des types incorrects
    - Message d'erreur approprié
    """
    schema = {"type": "object", "properties": {"age": {"type": "number"}}}

    guardrail = Guardrail(name="test_schema", schema=schema)

    # age est une string au lieu d'un nombre
    invalid_json = json.dumps({"age": "thirty"})
    is_valid, error = guardrail.validate(invalid_json)

    assert is_valid is False
    assert error is not None
    assert "JSONSchema validation failed" in error


@pytest.mark.unit
def test_guardrail_jsonschema_invalid_json_format():
    """
    Test de validation JSONSchema: format JSON invalide

    Vérifie:
    - Détection de JSON malformé
    - Message d'erreur "Invalid JSON format"
    """
    schema = {"type": "object", "properties": {"name": {"type": "string"}}}

    guardrail = Guardrail(name="test_schema", schema=schema)

    # JSON invalide
    invalid_json = "{name: 'Alice'"  # Manque guillemets et accolade fermante
    is_valid, error = guardrail.validate(invalid_json)

    assert is_valid is False
    assert error == "Invalid JSON format"


@pytest.mark.unit
def test_guardrail_jsonschema_nested_objects():
    """
    Test de validation JSONSchema: objets imbriqués

    Vérifie:
    - Validation d'objets JSON complexes
    - Support des structures imbriquées
    """
    schema = {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "address": {
                        "type": "object",
                        "properties": {"city": {"type": "string"}},
                        "required": ["city"],
                    },
                },
                "required": ["name", "address"],
            }
        },
        "required": ["user"],
    }

    guardrail = Guardrail(name="test_nested", schema=schema)

    valid_json = json.dumps({"user": {"name": "Alice", "address": {"city": "Montreal"}}})

    is_valid, error = guardrail.validate(valid_json)

    assert is_valid is True
    assert error is None


@pytest.mark.unit
def test_guardrail_jsonschema_arrays():
    """
    Test de validation JSONSchema: tableaux

    Vérifie:
    - Validation de tableaux JSON
    - Contraintes sur les éléments du tableau
    """
    schema = {
        "type": "object",
        "properties": {"tags": {"type": "array", "items": {"type": "string"}, "minItems": 1}},
        "required": ["tags"],
    }

    guardrail = Guardrail(name="test_array", schema=schema)

    # Tableau valide
    valid_json = json.dumps({"tags": ["tag1", "tag2", "tag3"]})
    is_valid, error = guardrail.validate(valid_json)

    assert is_valid is True
    assert error is None

    # Tableau vide (invalide à cause de minItems: 1)
    invalid_json = json.dumps({"tags": []})
    is_valid, error = guardrail.validate(invalid_json)

    assert is_valid is False
    assert "JSONSchema validation failed" in error


# ============================================================================
# TESTS: Guardrail - Regex Pattern Matching
# ============================================================================


@pytest.mark.unit
def test_guardrail_regex_pattern_valid():
    """
    Test de validation regex: pattern valide

    Vérifie:
    - Validation réussie pour texte correspondant au pattern
    - Pas d'erreur retournée
    """
    # Pattern pour email
    email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    guardrail = Guardrail(name="email_validator", pattern=email_pattern)

    valid_email = "user@example.com"
    is_valid, error = guardrail.validate(valid_email)

    assert is_valid is True
    assert error is None


@pytest.mark.unit
def test_guardrail_regex_pattern_invalid():
    """
    Test de validation regex: pattern invalide

    Vérifie:
    - Détection de texte ne correspondant pas au pattern
    - Message d'erreur approprié
    """
    email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    guardrail = Guardrail(name="email_validator", pattern=email_pattern)

    invalid_email = "not-an-email"
    is_valid, error = guardrail.validate(invalid_email)

    assert is_valid is False
    assert error == "Pattern validation failed for email_validator"


@pytest.mark.unit
def test_guardrail_regex_max_length():
    """
    Test de validation regex: longueur maximale

    Vérifie:
    - Validation de longueur de texte avec regex
    - Pattern pour max_length
    """
    # Pattern pour max 10 caractères
    max_length_pattern = r"^.{0,10}$"
    guardrail = Guardrail(name="max_length", pattern=max_length_pattern)

    # Texte valide (10 caractères)
    valid_text = "1234567890"
    is_valid, error = guardrail.validate(valid_text)
    assert is_valid is True

    # Texte invalide (11 caractères)
    invalid_text = "12345678901"
    is_valid, error = guardrail.validate(invalid_text)
    assert is_valid is False


@pytest.mark.unit
def test_guardrail_regex_phone_number():
    """
    Test de validation regex: numéro de téléphone

    Vérifie:
    - Validation de format de numéro de téléphone
    - Pattern pour format nord-américain
    """
    # Pattern pour numéro nord-américain: (XXX) XXX-XXXX
    phone_pattern = r"^\(\d{3}\) \d{3}-\d{4}$"
    guardrail = Guardrail(name="phone_validator", pattern=phone_pattern)

    valid_phone = "(514) 123-4567"
    is_valid, error = guardrail.validate(valid_phone)
    assert is_valid is True

    invalid_phone = "514-123-4567"
    is_valid, error = guardrail.validate(invalid_phone)
    assert is_valid is False


@pytest.mark.unit
def test_guardrail_regex_multiline():
    """
    Test de validation regex: texte multiligne

    Vérifie:
    - Validation de texte sur plusieurs lignes
    - Pattern avec support multiligne
    """
    # Pattern pour détecter la présence d'un mot
    pattern = r"important"
    guardrail = Guardrail(name="keyword_search", pattern=pattern)

    multiline_text = """
    This is a test.
    This is important information.
    End of text.
    """

    is_valid, error = guardrail.validate(multiline_text)
    assert is_valid is True


# ============================================================================
# TESTS: Guardrail - Blocklist
# ============================================================================


@pytest.mark.unit
def test_guardrail_blocklist_single_word():
    """
    Test de blocklist: mot unique

    Vérifie:
    - Détection de mot bloqué
    - Message d'erreur avec le mot détecté
    """
    blocklist = ["password", "secret", "confidential"]
    guardrail = Guardrail(name="blocklist_test", blocklist=blocklist)

    # Texte contenant un mot bloqué
    text_with_blocked = "This is a secret document"
    is_valid, error = guardrail.validate(text_with_blocked)

    assert is_valid is False
    assert error is not None
    assert "Blocked keyword detected" in error
    assert "secret" in error.lower()


@pytest.mark.unit
def test_guardrail_blocklist_case_insensitive():
    """
    Test de blocklist: insensible à la casse

    Vérifie:
    - Détection insensible à la casse
    - "PASSWORD" détecté même si blocklist contient "password"
    """
    blocklist = ["password"]
    guardrail = Guardrail(name="blocklist_test", blocklist=blocklist)

    # Différentes casses
    texts = ["My PASSWORD is secret", "my password is secret", "My PaSsWoRd is secret"]

    for text in texts:
        is_valid, error = guardrail.validate(text)
        assert is_valid is False
        assert "Blocked keyword detected" in error


@pytest.mark.unit
def test_guardrail_blocklist_multiple_words():
    """
    Test de blocklist: mots multiples

    Vérifie:
    - Détection de plusieurs mots bloqués
    - Premier mot bloqué déclenche l'erreur
    """
    blocklist = ["hack", "exploit", "malware"]
    guardrail = Guardrail(name="security_blocklist", blocklist=blocklist)

    text = "This is a hack attempt"
    is_valid, error = guardrail.validate(text)

    assert is_valid is False
    assert "hack" in error.lower()


@pytest.mark.unit
def test_guardrail_blocklist_no_match():
    """
    Test de blocklist: pas de correspondance

    Vérifie:
    - Validation réussie si aucun mot bloqué n'est détecté
    """
    blocklist = ["forbidden", "banned", "illegal"]
    guardrail = Guardrail(name="blocklist_test", blocklist=blocklist)

    safe_text = "This is a normal and safe text"
    is_valid, error = guardrail.validate(safe_text)

    assert is_valid is True
    assert error is None


@pytest.mark.unit
def test_guardrail_blocklist_empty():
    """
    Test de blocklist: liste vide

    Vérifie:
    - Comportement correct avec blocklist vide
    - Aucune validation de blocklist effectuée
    """
    guardrail = Guardrail(name="empty_blocklist", blocklist=[])

    text = "Any text should pass"
    is_valid, error = guardrail.validate(text)

    assert is_valid is True
    assert error is None


# ============================================================================
# TESTS: Guardrail - Allowedlist (TODO dans le code source)
# ============================================================================


@pytest.mark.unit
def test_guardrail_allowedlist():
    """
    Test de allowedlist: validation de valeurs autorisées

    Vérifie:
    - Validation de valeurs dans allowedlist
    - Rejet de valeurs hors allowedlist
    """
    allowedlist = ["approved", "verified", "trusted"]
    guardrail = Guardrail(name="allowedlist_test", allowedlist=allowedlist)

    # Valeur autorisée - exact match
    is_valid, error = guardrail.validate("approved")
    assert is_valid is True
    assert error is None

    # Valeur autorisée - with whitespace
    is_valid, error = guardrail.validate("  verified  ")
    assert is_valid is True
    assert error is None

    # Valeur autorisée - case insensitive
    is_valid, error = guardrail.validate("TRUSTED")
    assert is_valid is True
    assert error is None

    # Valeur NON autorisée
    is_valid, error = guardrail.validate("unauthorized")
    assert is_valid is False
    assert error is not None
    assert "not in allowedlist" in error

    # Valeur partielle autorisée (contient un mot de l'allowedlist)
    is_valid, error = guardrail.validate("This is approved by admin")
    assert is_valid is True
    assert error is None


# ============================================================================
# TESTS: Guardrail - Combinaisons de contraintes
# ============================================================================


@pytest.mark.unit
def test_guardrail_combined_blocklist_and_pattern():
    """
    Test de combinaison: blocklist + pattern regex

    Vérifie:
    - Application de plusieurs contraintes simultanément
    - Ordre de validation (blocklist vérifié en premier)
    """
    blocklist = ["forbidden"]
    email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"

    guardrail = Guardrail(name="combined_test", blocklist=blocklist, pattern=email_pattern)

    # Texte valide pour pattern mais contient mot bloqué
    text = "forbidden@example.com"
    is_valid, error = guardrail.validate(text)

    assert is_valid is False
    assert "Blocked keyword detected" in error

    # Texte sans mot bloqué mais pattern invalide
    text = "not-an-email"
    is_valid, error = guardrail.validate(text)

    assert is_valid is False
    assert "Pattern validation failed" in error

    # Texte valide pour les deux
    text = "valid@example.com"
    is_valid, error = guardrail.validate(text)

    assert is_valid is True
    assert error is None


@pytest.mark.unit
def test_guardrail_combined_schema_and_blocklist():
    """
    Test de combinaison: JSONSchema + blocklist

    Vérifie:
    - Application de contraintes JSONSchema et blocklist
    - Blocklist vérifié avant JSONSchema
    """
    blocklist = ["malicious"]
    schema = {
        "type": "object",
        "properties": {"message": {"type": "string"}},
        "required": ["message"],
    }

    guardrail = Guardrail(name="schema_blocklist", blocklist=blocklist, schema=schema)

    # JSON valide mais contient mot bloqué
    text = json.dumps({"message": "This is malicious content"})
    is_valid, error = guardrail.validate(text)

    assert is_valid is False
    assert "Blocked keyword detected" in error


# ============================================================================
# TESTS: ConstraintsEngine
# ============================================================================


@pytest.mark.unit
def test_constraints_engine_initialization(tmp_path):
    """
    Test d'initialisation du ConstraintsEngine

    Vérifie:
    - Initialisation correcte
    - Liste de guardrails vide si pas de config
    """
    # Config inexistante
    engine = ConstraintsEngine(config_path="nonexistent.yaml")

    assert engine.guardrails == []


@pytest.mark.unit
def test_constraints_engine_add_guardrail():
    """
    Test d'ajout de guardrail personnalisé

    Vérifie:
    - Ajout de guardrail via add_guardrail()
    - Guardrail accessible dans la liste
    """
    engine = ConstraintsEngine(config_path="nonexistent.yaml")

    guardrail = Guardrail(name="custom", pattern=r"^\d+$")
    engine.add_guardrail(guardrail)

    assert len(engine.guardrails) == 1
    assert engine.guardrails[0].name == "custom"


@pytest.mark.unit
def test_constraints_engine_validate_output_success():
    """
    Test de validation de sortie: succès

    Vérifie:
    - Validation réussie avec plusieurs guardrails
    - Aucune erreur retournée
    """
    engine = ConstraintsEngine(config_path="nonexistent.yaml")

    # Ajouter des guardrails
    engine.add_guardrail(Guardrail(name="length", pattern=r"^.{0,100}$"))
    engine.add_guardrail(Guardrail(name="blocklist", blocklist=["forbidden"]))

    text = "This is a valid output"
    is_valid, errors = engine.validate_output(text)

    assert is_valid is True
    assert errors == []


@pytest.mark.unit
def test_constraints_engine_validate_output_failure():
    """
    Test de validation de sortie: échec

    Vérifie:
    - Détection d'erreurs de validation
    - Liste d'erreurs retournée avec noms de guardrails
    """
    engine = ConstraintsEngine(config_path="nonexistent.yaml")

    engine.add_guardrail(Guardrail(name="length", pattern=r"^.{0,10}$"))
    engine.add_guardrail(Guardrail(name="blocklist", blocklist=["forbidden"]))

    # Texte trop long ET contient mot bloqué
    text = "This is a forbidden text that is too long"
    is_valid, errors = engine.validate_output(text)

    assert is_valid is False
    assert len(errors) == 2  # Deux erreurs détectées
    assert any("length" in err for err in errors)
    assert any("blocklist" in err for err in errors)


@pytest.mark.unit
def test_constraints_engine_validate_output_multiple_guardrails():
    """
    Test de validation avec plusieurs guardrails

    Vérifie:
    - Tous les guardrails sont appliqués
    - Erreurs accumulées correctement
    """
    engine = ConstraintsEngine(config_path="nonexistent.yaml")

    # Ajouter plusieurs guardrails
    guardrails = [
        Guardrail(name="g1", blocklist=["bad1"]),
        Guardrail(name="g2", blocklist=["bad2"]),
        Guardrail(name="g3", blocklist=["bad3"]),
    ]

    for g in guardrails:
        engine.add_guardrail(g)

    # Texte contenant deux mots bloqués
    text = "This contains bad1 and bad2"
    is_valid, errors = engine.validate_output(text)

    assert is_valid is False
    assert len(errors) == 2


@pytest.mark.unit
def test_constraints_engine_validate_json_output_valid():
    """
    Test de validation JSON: données valides

    Vérifie:
    - Méthode validate_json_output()
    - Validation JSONSchema réussie
    """
    engine = ConstraintsEngine(config_path="nonexistent.yaml")

    schema = {
        "type": "object",
        "properties": {"status": {"type": "string"}},
        "required": ["status"],
    }

    valid_json = json.dumps({"status": "success"})
    is_valid, error = engine.validate_json_output(valid_json, schema)

    assert is_valid is True
    assert error is None


@pytest.mark.unit
def test_constraints_engine_validate_json_output_invalid_schema():
    """
    Test de validation JSON: schéma invalide

    Vérifie:
    - Détection d'erreur de schéma
    - Message d'erreur approprié
    """
    engine = ConstraintsEngine(config_path="nonexistent.yaml")

    schema = {"type": "object", "properties": {"count": {"type": "number"}}, "required": ["count"]}

    # count manquant
    invalid_json = json.dumps({"status": "success"})
    is_valid, error = engine.validate_json_output(invalid_json, schema)

    assert is_valid is False
    assert "Schema validation failed" in error


@pytest.mark.unit
def test_constraints_engine_validate_json_output_invalid_format():
    """
    Test de validation JSON: format invalide

    Vérifie:
    - Détection de JSON malformé
    - Message d'erreur "Invalid JSON"
    """
    engine = ConstraintsEngine(config_path="nonexistent.yaml")

    schema = {"type": "object"}

    invalid_json = "not valid json"
    is_valid, error = engine.validate_json_output(invalid_json, schema)

    assert is_valid is False
    assert "Invalid JSON" in error


# ============================================================================
# TESTS: ConstraintsEngine - Configuration YAML
# ============================================================================


@pytest.mark.unit
def test_constraints_engine_load_from_config(tmp_path):
    """
    Test de chargement depuis config YAML

    Vérifie:
    - Chargement de guardrails depuis policies.yaml
    - Création automatique de guardrails
    """
    # Créer un fichier de config temporaire
    config_file = tmp_path / "policies.yaml"
    config_content = """
policies:
  guardrails:
    enabled: true
    blocklist_keywords:
      - "forbidden"
      - "banned"
    max_prompt_length: 100
    max_response_length: 500
"""
    config_file.write_text(config_content)

    engine = ConstraintsEngine(config_path=str(config_file))

    # Vérifier que les guardrails ont été créés
    assert len(engine.guardrails) > 0

    # Vérifier le guardrail de blocklist
    blocklist_guardrail = next(
        (g for g in engine.guardrails if g.name == "keyword_blocklist"), None
    )
    assert blocklist_guardrail is not None
    assert "forbidden" in blocklist_guardrail.blocklist
    assert "banned" in blocklist_guardrail.blocklist


@pytest.mark.unit
def test_constraints_engine_load_from_config_disabled(tmp_path):
    """
    Test de chargement avec guardrails désactivés

    Vérifie:
    - Aucun guardrail créé si enabled: false
    """
    config_file = tmp_path / "policies.yaml"
    config_content = """
policies:
  guardrails:
    enabled: false
    blocklist_keywords:
      - "forbidden"
"""
    config_file.write_text(config_content)

    engine = ConstraintsEngine(config_path=str(config_file))

    # Aucun guardrail ne devrait être créé
    assert len(engine.guardrails) == 0


@pytest.mark.unit
def test_constraints_engine_max_length_guardrails(tmp_path):
    """
    Test des guardrails de longueur maximale

    Vérifie:
    - Création de guardrails pour max_prompt_length
    - Création de guardrails pour max_response_length
    """
    config_file = tmp_path / "policies.yaml"
    config_content = """
policies:
  guardrails:
    enabled: true
    max_prompt_length: 50
    max_response_length: 100
"""
    config_file.write_text(config_content)

    engine = ConstraintsEngine(config_path=str(config_file))

    # Vérifier les guardrails de longueur
    max_prompt_guardrail = next(
        (g for g in engine.guardrails if g.name == "max_prompt_length"), None
    )
    max_response_guardrail = next(
        (g for g in engine.guardrails if g.name == "max_response_length"), None
    )

    assert max_prompt_guardrail is not None
    assert max_response_guardrail is not None


# ============================================================================
# TESTS: Singleton Pattern
# ============================================================================


@pytest.mark.unit
def test_get_constraints_engine_singleton():
    """
    Test du pattern singleton

    Vérifie:
    - get_constraints_engine() retourne toujours la même instance
    """
    engine1 = get_constraints_engine()
    engine2 = get_constraints_engine()

    assert engine1 is engine2


@pytest.mark.unit
def test_init_constraints_engine_creates_new_instance(tmp_path):
    """
    Test de réinitialisation du singleton

    Vérifie:
    - init_constraints_engine() crée une nouvelle instance
    """
    # Obtenir l'instance actuelle
    engine1 = get_constraints_engine()

    # Réinitialiser avec une nouvelle config
    config_file = tmp_path / "new_policies.yaml"
    config_file.write_text("policies:\n  guardrails:\n    enabled: false\n")

    engine2 = init_constraints_engine(config_path=str(config_file))

    # Nouvelle instance créée
    assert engine1 is not engine2

    # get_constraints_engine() retourne la nouvelle instance
    engine3 = get_constraints_engine()
    assert engine3 is engine2


# ============================================================================
# TESTS: Edge Cases et Robustesse
# ============================================================================


@pytest.mark.unit
def test_guardrail_empty_text():
    """
    Test de robustesse: texte vide

    Vérifie:
    - Comportement correct avec texte vide
    """
    guardrail = Guardrail(name="test", blocklist=["forbidden"])

    is_valid, error = guardrail.validate("")

    assert is_valid is True
    assert error is None


@pytest.mark.unit
def test_guardrail_whitespace_only():
    """
    Test de robustesse: espaces uniquement

    Vérifie:
    - Validation de texte contenant uniquement des espaces
    """
    guardrail = Guardrail(name="test", pattern=r"^\s+$")

    is_valid, error = guardrail.validate("   ")

    assert is_valid is True
    assert error is None


@pytest.mark.unit
def test_guardrail_special_characters():
    """
    Test de robustesse: caractères spéciaux

    Vérifie:
    - Gestion correcte de caractères spéciaux Unicode
    """
    guardrail = Guardrail(name="test", blocklist=["interdit"])

    text = "Texte avec accents: éàùç and émojis: 🚀"
    is_valid, error = guardrail.validate(text)

    assert is_valid is True
    assert error is None


@pytest.mark.unit
def test_guardrail_very_long_text():
    """
    Test de robustesse: texte très long

    Vérifie:
    - Performance avec texte de grande taille
    """
    guardrail = Guardrail(name="test", blocklist=["needle"])

    # Texte de 10000 caractères
    long_text = "a" * 10000
    is_valid, error = guardrail.validate(long_text)

    assert is_valid is True

    # Texte long avec mot bloqué à la fin
    long_text_with_blocked = "a" * 9990 + "needle"
    is_valid, error = guardrail.validate(long_text_with_blocked)

    assert is_valid is False


@pytest.mark.unit
def test_constraints_engine_no_guardrails():
    """
    Test de robustesse: aucun guardrail configuré

    Vérifie:
    - Validation réussit si aucun guardrail
    """
    engine = ConstraintsEngine(config_path="nonexistent.yaml")

    is_valid, errors = engine.validate_output("Any text")

    assert is_valid is True
    assert errors == []


# ============================================================================
# TESTS: Compliance - Constraint Violation Handling
# ============================================================================


@pytest.mark.compliance
def test_constraint_violation_detailed_error_messages():
    """
    Test de conformité: messages d'erreur détaillés

    Vérifie:
    - Messages d'erreur incluent le nom du guardrail
    - Messages d'erreur sont informatifs
    """
    engine = ConstraintsEngine(config_path="nonexistent.yaml")

    engine.add_guardrail(Guardrail(name="security_check", blocklist=["hack"]))
    engine.add_guardrail(Guardrail(name="length_check", pattern=r"^.{0,10}$"))

    text = "This is a hack attempt that is too long"
    is_valid, errors = engine.validate_output(text)

    assert is_valid is False
    assert len(errors) == 2

    # Vérifier que les noms de guardrails sont dans les erreurs
    error_string = " ".join(errors)
    assert "security_check" in error_string
    assert "length_check" in error_string


@pytest.mark.compliance
def test_constraint_violation_order_of_execution():
    """
    Test de conformité: ordre d'exécution des contraintes

    Vérifie:
    - Blocklist vérifié avant pattern
    - Pattern vérifié avant JSONSchema
    """
    # Guardrail avec blocklist, pattern et schema
    schema = {"type": "object", "properties": {"key": {"type": "string"}}}
    guardrail = Guardrail(
        name="multi_constraint", blocklist=["forbidden"], pattern=r"^.{0,20}$", schema=schema
    )

    # Texte contenant mot bloqué (doit échouer sur blocklist en premier)
    text = "forbidden"
    is_valid, error = guardrail.validate(text)

    assert is_valid is False
    assert "Blocked keyword detected" in error  # Blocklist vérifié en premier


@pytest.mark.compliance
def test_pii_detection_in_constraints():
    """
    Test de conformité: détection de PII dans les contraintes

    Vérifie:
    - Blocklist peut détecter des patterns PII simples
    - Numéros de carte de crédit, SSN, etc. peuvent être bloqués
    """
    # Guardrails pour détecter PII
    pii_patterns = [
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN format XXX-XX-XXXX
        r"\b\d{16}\b",  # Credit card (16 digits)
    ]

    engine = ConstraintsEngine(config_path="nonexistent.yaml")

    # Ajouter des guardrails pour chaque pattern PII
    for i, pattern in enumerate(pii_patterns):
        engine.add_guardrail(Guardrail(name=f"pii_check_{i}", pattern=f"^((?!{pattern}).)*$"))

    # Texte sûr
    safe_text = "This is normal text"
    is_valid, errors = engine.validate_output(safe_text)
    assert is_valid is True

    # Note: Tests plus sophistiqués de PII sont dans redaction.py


# ============================================================================
# TESTS: Integration avec autres middlewares
# ============================================================================


@pytest.mark.integration
def test_constraints_integration_with_logging(isolated_logging):
    """
    Test d'intégration: constraints + logging

    Vérifie:
    - Les violations de contraintes peuvent être loguées
    - Structure de log appropriée
    """
    engine = ConstraintsEngine(config_path="nonexistent.yaml")
    engine.add_guardrail(Guardrail(name="test", blocklist=["forbidden"]))

    logger = isolated_logging["event_logger"]

    text = "This contains forbidden word"
    is_valid, errors = engine.validate_output(text)

    # Logger la violation
    if not is_valid:
        logger.log_event(
            actor="constraints_engine",
            event="constraint.violation",
            level="WARNING",
            metadata={"errors": errors},
        )

    # Vérifier que l'événement a été logué
    event_files = list(isolated_logging["event_log_dir"].glob("*.jsonl"))
    assert len(event_files) > 0

    # Lire le dernier événement
    with open(event_files[-1], "r") as f:
        last_line = f.readlines()[-1]
        event = json.loads(last_line)

        assert event["event"] == "constraint.violation"
        assert event["level"] == "WARNING"


@pytest.mark.unit
def test_constraints_with_decision_records_metadata():
    """
    Test d'intégration: contraintes dans Decision Records

    Vérifie:
    - Les violations de contraintes peuvent être incluses dans DR metadata
    """
    engine = ConstraintsEngine(config_path="nonexistent.yaml")
    engine.add_guardrail(Guardrail(name="safety", blocklist=["unsafe"]))

    text = "This is an unsafe operation"
    is_valid, errors = engine.validate_output(text)

    # Métadonnées pour Decision Record
    dr_metadata = {
        "constraint_validation": {
            "is_valid": is_valid,
            "errors": errors,
            "guardrails_applied": [g.name for g in engine.guardrails],
        }
    }

    assert dr_metadata["constraint_validation"]["is_valid"] is False
    assert len(dr_metadata["constraint_validation"]["errors"]) > 0
    assert "safety" in dr_metadata["constraint_validation"]["guardrails_applied"]
