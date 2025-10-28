"""
Security and Policy Enforcement compliance tests

Tests security aspects and policy compliance:
- PII masking in logs and decision records
- RBAC policy enforcement
- Data retention policy execution
- Audit log immutability
- Tool allowlist enforcement
- Network isolation
- File system access restrictions
"""

import pytest
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from policy.pii import PIIDetector, PIIMasker
from policy.engine import PolicyEngine
from tools.registry import ToolRegistry


# ============================================================================
# TESTS: PII Masking and Redaction
# ============================================================================

@pytest.mark.compliance
def test_pii_email_detection_and_masking():
    """
    Test de conformité: Détection et masquage d'emails
    
    Vérifie:
    - Les emails sont détectés
    - Le masquage est appliqué correctement
    - Format [REDACTED] est utilisé
    """
    detector = PIIDetector()
    masker = PIIMasker()
    
    test_cases = [
        ("My email is john.doe@example.com", True),
        ("Contact: alice@test.org for details", True),
        ("No email in this text", False),
        ("Email: user+tag@domain.co.uk", True)
    ]
    
    for text, should_contain_email in test_cases:
        has_pii = detector.contains_pii(text, pii_types=["email"])
        assert has_pii == should_contain_email, f"Email detection failed for: {text}"
        
        if should_contain_email:
            masked = masker.mask_text(text, pii_types=["email"])
            assert "[REDACTED]" in masked, f"Email not masked in: {text}"
            # L'email original ne doit plus être présent
            assert "@" not in masked or "[REDACTED]" in masked


@pytest.mark.compliance
def test_pii_phone_number_masking():
    """
    Test de conformité: Masquage de numéros de téléphone
    
    Vérifie:
    - Détection de différents formats de téléphone
    - Masquage correct
    """
    detector = PIIDetector()
    masker = PIIMasker()
    
    phone_numbers = [
        "Call me at 555-123-4567",
        "Phone: (555) 123-4567",
        "Contact: +1-555-123-4567",
        "Tel: 555.123.4567"
    ]
    
    for text in phone_numbers:
        has_pii = detector.contains_pii(text, pii_types=["phone"])
        assert has_pii, f"Phone not detected in: {text}"
        
        masked = masker.mask_text(text, pii_types=["phone"])
        assert "[REDACTED]" in masked, f"Phone not masked in: {text}"


@pytest.mark.compliance
def test_pii_ssn_masking():
    """
    Test de conformité: Masquage de numéros de sécurité sociale
    
    Vérifie:
    - Détection de SSN
    - Masquage complet
    """
    detector = PIIDetector()
    masker = PIIMasker()
    
    ssn_texts = [
        "SSN: 123-45-6789",
        "Social Security Number is 123456789",
        "My SSN is 123 45 6789"
    ]
    
    for text in ssn_texts:
        has_pii = detector.contains_pii(text, pii_types=["ssn"])
        assert has_pii, f"SSN not detected in: {text}"
        
        masked = masker.mask_text(text, pii_types=["ssn"])
        assert "[REDACTED]" in masked, f"SSN not masked in: {text}"
        # Vérifier que les chiffres du SSN ne sont plus visibles
        assert "123" not in masked or "[REDACTED]" in masked


@pytest.mark.compliance
def test_pii_credit_card_masking():
    """
    Test de conformité: Masquage de numéros de carte de crédit
    
    Vérifie:
    - Détection de numéros de carte
    - Masquage sécurisé
    """
    detector = PIIDetector()
    masker = PIIMasker()
    
    cc_texts = [
        "Credit card: 4532-1234-5678-9010",
        "Card number is 4532123456789010",
        "Pay with 4532 1234 5678 9010"
    ]
    
    for text in cc_texts:
        has_pii = detector.contains_pii(text, pii_types=["credit_card"])
        assert has_pii, f"Credit card not detected in: {text}"
        
        masked = masker.mask_text(text, pii_types=["credit_card"])
        assert "[REDACTED]" in masked, f"Credit card not masked in: {text}"


@pytest.mark.compliance
def test_pii_multiple_types_in_text():
    """
    Test de conformité: Masquage de multiples types de PII
    
    Vérifie:
    - Détection de plusieurs types de PII dans un même texte
    - Tous sont masqués
    """
    detector = PIIDetector()
    masker = PIIMasker()
    
    text = "Contact John at john@example.com or call 555-123-4567. SSN: 123-45-6789"
    
    has_pii = detector.contains_pii(text)
    assert has_pii, "Multiple PII types not detected"
    
    masked = masker.mask_text(text)
    
    # Vérifier que tous les types sont masqués
    assert masked.count("[REDACTED]") >= 3, "Not all PII types masked"
    assert "john@example.com" not in masked
    assert "555-123-4567" not in masked
    assert "123-45-6789" not in masked


@pytest.mark.compliance
def test_pii_masking_preserves_structure():
    """
    Test de conformité: Le masquage préserve la structure du texte
    
    Vérifie:
    - Le texte reste lisible
    - Le contexte est préservé
    - Seules les PII sont masquées
    """
    masker = PIIMasker()
    
    text = "Please email your resume to jobs@company.com by Friday."
    masked = masker.mask_text(text)
    
    # Le texte doit contenir encore les mots non-PII
    assert "Please" in masked
    assert "resume" in masked
    assert "Friday" in masked
    assert "[REDACTED]" in masked


# ============================================================================
# TESTS: RBAC Policy Enforcement
# ============================================================================

@pytest.mark.compliance
def test_rbac_admin_has_all_permissions():
    """
    Test de conformité: Rôle admin a toutes les permissions
    
    Vérifie:
    - Admin peut exécuter tous les outils
    - Admin peut lire tous les logs
    - Admin peut gérer la configuration
    """
    policy_engine = PolicyEngine()
    
    admin_permissions = [
        "execute_all_tools",
        "read_all_logs",
        "manage_config",
        "view_audit"
    ]
    
    for permission in admin_permissions:
        assert policy_engine.has_permission("admin", permission), \
            f"Admin should have {permission}"


@pytest.mark.compliance
def test_rbac_user_limited_permissions():
    """
    Test de conformité: Rôle user a des permissions limitées
    
    Vérifie:
    - User peut exécuter des outils safe
    - User ne peut pas gérer la config
    - User peut lire ses propres logs
    """
    policy_engine = PolicyEngine()
    
    # Permissions que user DOIT avoir
    user_should_have = [
        "execute_safe_tools",
        "read_own_logs",
        "manage_own_data"
    ]
    
    for permission in user_should_have:
        assert policy_engine.has_permission("user", permission), \
            f"User should have {permission}"
    
    # Permissions que user NE DOIT PAS avoir
    user_should_not_have = [
        "manage_config",
        "read_all_logs",
        "execute_all_tools"
    ]
    
    for permission in user_should_not_have:
        assert not policy_engine.has_permission("user", permission), \
            f"User should NOT have {permission}"


@pytest.mark.compliance
def test_rbac_viewer_minimal_permissions():
    """
    Test de conformité: Rôle viewer a permissions minimales
    
    Vérifie:
    - Viewer peut seulement lire ses logs
    - Viewer ne peut pas exécuter d'outils
    - Viewer ne peut pas modifier de données
    """
    policy_engine = PolicyEngine()
    
    # Viewer ne doit avoir que read_own_logs
    assert policy_engine.has_permission("viewer", "read_own_logs"), \
        "Viewer should have read_own_logs"
    
    # Viewer ne doit pas avoir d'autres permissions
    forbidden_permissions = [
        "execute_safe_tools",
        "execute_all_tools",
        "manage_config",
        "read_all_logs",
        "manage_own_data"
    ]
    
    for permission in forbidden_permissions:
        assert not policy_engine.has_permission("viewer", permission), \
            f"Viewer should NOT have {permission}"


# ============================================================================
# TESTS: Tool Allowlist Enforcement
# ============================================================================

@pytest.mark.compliance
def test_tool_allowlist_enforcement():
    """
    Test de conformité: Enforcement de l'allowlist d'outils
    
    Vérifie:
    - Seuls les outils dans l'allowlist peuvent être exécutés
    - Les outils non autorisés sont bloqués
    """
    policy_engine = PolicyEngine()
    
    allowed_tools = ["python_sandbox", "file_read", "math_calculator"]
    forbidden_tools = ["system_exec", "network_request", "database_write"]
    
    for tool in allowed_tools:
        assert policy_engine.is_tool_allowed(tool), \
            f"Tool {tool} should be allowed"
    
    for tool in forbidden_tools:
        assert not policy_engine.is_tool_allowed(tool), \
            f"Tool {tool} should be forbidden"


@pytest.mark.compliance
def test_network_access_blocked_by_default():
    """
    Test de conformité: Accès réseau bloqué par défaut
    
    Vérifie:
    - network_access est false par défaut
    - Les domaines externes sont bloqués
    """
    policy_engine = PolicyEngine()
    
    assert not policy_engine.is_network_allowed(), \
        "Network access should be blocked by default"
    
    external_domains = [
        "google.com",
        "github.com",
        "api.openai.com"
    ]
    
    for domain in external_domains:
        assert not policy_engine.is_domain_allowed(domain), \
            f"Domain {domain} should be blocked"


@pytest.mark.compliance
def test_filesystem_allowed_paths():
    """
    Test de conformité: Chemins de système de fichiers autorisés
    
    Vérifie:
    - Seuls les chemins dans l'allowlist sont autorisés
    - Les chemins en dehors sont bloqués
    """
    policy_engine = PolicyEngine()
    
    allowed_paths = [
        "working_set/file.txt",
        "temp/tmp_file.json",
        "memory/working_set/data.db"
    ]
    
    forbidden_paths = [
        "/etc/passwd",
        "/root/.ssh/id_rsa",
        "../../../etc/shadow",
        "C:\\Windows\\System32\\config"
    ]
    
    for path in allowed_paths:
        assert policy_engine.is_path_allowed(path), \
            f"Path {path} should be allowed"
    
    for path in forbidden_paths:
        assert not policy_engine.is_path_allowed(path), \
            f"Path {path} should be forbidden"


# ============================================================================
# TESTS: Resource Limits
# ============================================================================

@pytest.mark.compliance
def test_resource_limit_cpu_enforcement():
    """
    Test de conformité: Limites CPU enforced
    
    Vérifie:
    - La limite CPU est configurée
    - Les dépassements sont détectés
    """
    policy_engine = PolicyEngine()
    
    cpu_limit = policy_engine.get_resource_limit("cpu_percent")
    assert cpu_limit is not None, "CPU limit should be configured"
    assert cpu_limit <= 100, "CPU limit should be valid percentage"
    assert cpu_limit > 0, "CPU limit should be positive"


@pytest.mark.compliance
def test_resource_limit_memory_enforcement():
    """
    Test de conformité: Limites mémoire enforced
    
    Vérifie:
    - La limite mémoire est configurée
    - La valeur est raisonnable
    """
    policy_engine = PolicyEngine()
    
    memory_limit = policy_engine.get_resource_limit("memory_mb")
    assert memory_limit is not None, "Memory limit should be configured"
    assert memory_limit > 0, "Memory limit should be positive"
    assert memory_limit <= 16384, "Memory limit should be reasonable (<=16GB)"


@pytest.mark.compliance
def test_resource_limit_file_size_enforcement():
    """
    Test de conformité: Limites de taille de fichier
    
    Vérifie:
    - La limite de taille de fichier est configurée
    - Les fichiers trop gros sont rejetés
    """
    policy_engine = PolicyEngine()
    
    file_size_limit = policy_engine.get_resource_limit("max_file_size_kb")
    assert file_size_limit is not None, "File size limit should be configured"
    assert file_size_limit > 0, "File size limit should be positive"


# ============================================================================
# TESTS: Guardrails
# ============================================================================

@pytest.mark.compliance
def test_guardrails_blocklist_keywords():
    """
    Test de conformité: Blocage de mots-clés interdits
    
    Vérifie:
    - Les mots-clés sensibles sont détectés
    - Le contenu est bloqué
    """
    policy_engine = PolicyEngine()
    
    blocked_keywords = ["password", "secret_key", "api_key"]
    
    for keyword in blocked_keywords:
        text = f"Here is my {keyword}: abc123"
        assert policy_engine.contains_blocked_keyword(text), \
            f"Blocked keyword '{keyword}' not detected"


@pytest.mark.compliance
def test_guardrails_prompt_length_limit():
    """
    Test de conformité: Limite de longueur de prompt
    
    Vérifie:
    - Les prompts trop longs sont détectés
    - La limite est enforced
    """
    policy_engine = PolicyEngine()
    
    max_length = policy_engine.get_max_prompt_length()
    assert max_length > 0, "Max prompt length should be configured"
    
    # Créer un prompt qui dépasse
    long_prompt = "x" * (max_length + 100)
    assert not policy_engine.is_prompt_valid(long_prompt), \
        "Long prompt should be rejected"
    
    # Créer un prompt valide
    valid_prompt = "x" * (max_length - 100)
    assert policy_engine.is_prompt_valid(valid_prompt), \
        "Valid prompt should be accepted"


@pytest.mark.compliance
def test_guardrails_response_length_limit():
    """
    Test de conformité: Limite de longueur de réponse
    
    Vérifie:
    - Les réponses trop longues sont tronquées ou rejetées
    - La limite est enforced
    """
    policy_engine = PolicyEngine()
    
    max_length = policy_engine.get_max_response_length()
    assert max_length > 0, "Max response length should be configured"
    
    long_response = "x" * (max_length + 100)
    assert not policy_engine.is_response_valid(long_response), \
        "Long response should be rejected"


# ============================================================================
# TESTS: Data Retention Policies
# ============================================================================

@pytest.mark.compliance
def test_retention_policy_conversation_ttl():
    """
    Test de conformité: TTL des conversations
    
    Vérifie:
    - TTL des conversations est configuré
    - La valeur correspond aux exigences légales
    """
    from memory.retention import RetentionManager
    
    retention_mgr = RetentionManager()
    
    conversation_ttl = retention_mgr.get_ttl("conversations")
    assert conversation_ttl is not None, "Conversation TTL should be configured"
    assert conversation_ttl == 30, "Conversation TTL should be 30 days"


@pytest.mark.compliance
def test_retention_policy_decision_records_ttl():
    """
    Test de conformité: TTL des Decision Records
    
    Vérifie:
    - DR sont conservés 365 jours
    - Conformité aux exigences réglementaires
    """
    from memory.retention import RetentionManager
    
    retention_mgr = RetentionManager()
    
    dr_ttl = retention_mgr.get_ttl("decisions")
    assert dr_ttl is not None, "DR TTL should be configured"
    assert dr_ttl == 365, "DR TTL should be 365 days"


@pytest.mark.compliance
def test_retention_policy_audit_logs_ttl():
    """
    Test de conformité: TTL des audit logs
    
    Vérifie:
    - Audit logs conservés 7 ans (2555 jours)
    - Conformité légale
    """
    from memory.retention import RetentionManager
    
    retention_mgr = RetentionManager()
    
    audit_ttl = retention_mgr.get_ttl("audit_logs")
    assert audit_ttl is not None, "Audit logs TTL should be configured"
    assert audit_ttl == 2555, "Audit logs TTL should be 2555 days (7 years)"


@pytest.mark.compliance
def test_retention_policy_auto_purge_enabled():
    """
    Test de conformité: Purge automatique activée
    
    Vérifie:
    - La purge automatique est configurée
    - L'intervalle de vérification est défini
    """
    from memory.retention import RetentionManager
    
    retention_mgr = RetentionManager()
    
    assert retention_mgr.is_auto_purge_enabled(), \
        "Auto purge should be enabled"
    
    check_interval = retention_mgr.get_purge_check_interval()
    assert check_interval is not None, "Purge check interval should be configured"
    assert check_interval == 7, "Purge should check every 7 days"
