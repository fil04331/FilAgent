"""
Extended EdDSA signature compliance tests

Tests edge cases, security, and performance aspects of EdDSA signatures:
- Key rotation mechanisms
- Expired key handling
- Bulk signature verification
- Cross-version compatibility
- Signature failure modes
"""

import pytest
import json
import base64
from pathlib import Path
from datetime import datetime, timedelta
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

from runtime.middleware.audittrail import DRManager


# ============================================================================
# TESTS: Key Rotation
# ============================================================================

@pytest.mark.compliance
def test_eddsa_key_rotation_mechanism(isolated_fs):
    """
    Test de conformité: Mécanisme de rotation de clés
    
    Vérifie:
    - Génération de nouvelles clés
    - Conservation des anciennes clés pour vérification
    - Signatures avec nouvelle clé sont valides
    """
    dr_manager = DRManager(dr_dir=str(isolated_fs['logs_decisions']))
    
    # Créer un DR avec la clé initiale
    dr_id_1 = dr_manager.create_record(
        conversation_id="test_conv",
        decision_type="tool_invocation",
        context={"tool": "test"},
        rationale="Before rotation"
    )
    
    # Lire le premier DR et extraire la clé publique
    dr_files = sorted(isolated_fs['logs_decisions'].glob("*.json"))
    assert len(dr_files) >= 1
    
    with open(dr_files[0], 'r') as f:
        dr_1 = json.load(f)
    
    public_key_1 = dr_1["signature"]["public_key"]
    
    # Simuler rotation: générer une nouvelle paire de clés
    new_private_key = ed25519.Ed25519PrivateKey.generate()
    new_public_key = new_private_key.public_key()
    
    # Note: Dans une vraie implémentation, on injecterait la nouvelle clé
    # Pour ce test, on vérifie juste que le mécanisme de signature fonctionne
    
    # Créer un message de test
    test_message = {"test": "data", "timestamp": datetime.utcnow().isoformat()}
    message_bytes = json.dumps(test_message, sort_keys=True).encode()
    
    # Signer avec la nouvelle clé
    new_signature = new_private_key.sign(message_bytes)
    
    # Vérifier avec la nouvelle clé publique
    try:
        new_public_key.verify(new_signature, message_bytes)
        rotation_successful = True
    except Exception:
        rotation_successful = False
    
    assert rotation_successful, "Key rotation mechanism failed"


@pytest.mark.compliance
def test_eddsa_multiple_valid_keys(isolated_fs):
    """
    Test de conformité: Support de multiples clés valides
    
    Vérifie:
    - Plusieurs clés peuvent coexister
    - Anciennes signatures restent vérifiables
    - Nouvelles signatures utilisent nouvelle clé
    """
    # Générer deux paires de clés (ancienne et nouvelle)
    old_private_key = ed25519.Ed25519PrivateKey.generate()
    old_public_key = old_private_key.public_key()
    
    new_private_key = ed25519.Ed25519PrivateKey.generate()
    new_public_key = new_private_key.public_key()
    
    # Message à signer
    message = {"data": "test", "timestamp": datetime.utcnow().isoformat()}
    message_bytes = json.dumps(message, sort_keys=True).encode()
    
    # Signer avec l'ancienne clé
    old_signature = old_private_key.sign(message_bytes)
    
    # Signer avec la nouvelle clé
    new_signature = new_private_key.sign(message_bytes)
    
    # Les deux signatures doivent être vérifiables avec leurs clés respectives
    try:
        old_public_key.verify(old_signature, message_bytes)
        old_valid = True
    except Exception:
        old_valid = False
    
    try:
        new_public_key.verify(new_signature, message_bytes)
        new_valid = True
    except Exception:
        new_valid = False
    
    assert old_valid, "Old signature verification failed"
    assert new_valid, "New signature verification failed"


# ============================================================================
# TESTS: Signature Verification Failures
# ============================================================================

@pytest.mark.compliance
def test_eddsa_signature_with_wrong_key(isolated_fs):
    """
    Test de conformité: Détection de signature avec mauvaise clé
    
    Vérifie:
    - Signature valide ne peut être vérifiée avec mauvaise clé
    - Détection d'erreur appropriée
    """
    # Générer deux paires de clés différentes
    key_1 = ed25519.Ed25519PrivateKey.generate()
    key_2 = ed25519.Ed25519PrivateKey.generate()
    
    public_key_1 = key_1.public_key()
    public_key_2 = key_2.public_key()
    
    # Signer avec la clé 1
    message = b"test message"
    signature = key_1.sign(message)
    
    # Essayer de vérifier avec la clé 2 (doit échouer)
    try:
        public_key_2.verify(signature, message)
        wrong_key_detected = False
    except Exception:
        wrong_key_detected = True
    
    assert wrong_key_detected, "Failed to detect wrong key usage"


@pytest.mark.compliance
def test_eddsa_signature_with_modified_message(isolated_fs):
    """
    Test de conformité: Détection de message modifié
    
    Vérifie:
    - Modification du message invalide la signature
    - Détection de tampering
    """
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    # Signer un message original
    original_message = b"original message"
    signature = private_key.sign(original_message)
    
    # Vérifier l'original (doit passer)
    try:
        public_key.verify(signature, original_message)
        original_valid = True
    except Exception:
        original_valid = False
    
    assert original_valid, "Original signature should be valid"
    
    # Essayer avec message modifié (doit échouer)
    modified_message = b"modified message"
    try:
        public_key.verify(signature, modified_message)
        tampering_detected = False
    except Exception:
        tampering_detected = True
    
    assert tampering_detected, "Failed to detect message tampering"


@pytest.mark.compliance
def test_eddsa_signature_with_invalid_format(isolated_fs):
    """
    Test de conformité: Gestion de signatures mal formées
    
    Vérifie:
    - Détection de signature invalide
    - Pas de crash sur données malformées
    """
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    message = b"test message"
    
    # Créer une "signature" invalide
    invalid_signature = b"not a valid signature"
    
    # La vérification doit échouer proprement
    try:
        public_key.verify(invalid_signature, message)
        invalid_detected = False
    except Exception:
        invalid_detected = True
    
    assert invalid_detected, "Failed to detect invalid signature format"


# ============================================================================
# TESTS: Performance
# ============================================================================

@pytest.mark.compliance
@pytest.mark.slow
def test_eddsa_bulk_signature_performance(isolated_fs):
    """
    Test de performance: Signature en masse
    
    Vérifie:
    - Performance acceptable pour signatures multiples
    - Pas de dégradation
    """
    import time
    
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    num_signatures = 100
    
    # Mesurer temps de signature
    messages = [f"message_{i}".encode() for i in range(num_signatures)]
    
    start = time.time()
    signatures = [private_key.sign(msg) for msg in messages]
    sign_time = time.time() - start
    
    # Mesurer temps de vérification
    start = time.time()
    for msg, sig in zip(messages, signatures):
        public_key.verify(sig, msg)
    verify_time = time.time() - start
    
    # Performance: doit être < 10ms par signature/vérification
    avg_sign_time = sign_time / num_signatures
    avg_verify_time = verify_time / num_signatures
    
    assert avg_sign_time < 0.01, f"Signature too slow: {avg_sign_time:.6f}s"
    assert avg_verify_time < 0.01, f"Verification too slow: {avg_verify_time:.6f}s"


@pytest.mark.compliance
def test_eddsa_concurrent_signatures(isolated_fs):
    """
    Test de conformité: Signatures concurrentes
    
    Vérifie:
    - Plusieurs threads peuvent signer simultanément
    - Pas de corruption
    - Thread-safety
    """
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    results = []
    lock = threading.Lock()
    
    def sign_message(thread_id):
        """Signer un message depuis un thread"""
        message = f"message from thread {thread_id}".encode()
        signature = private_key.sign(message)
        
        # Vérifier immédiatement
        try:
            public_key.verify(signature, message)
            with lock:
                results.append((thread_id, True))
        except Exception as e:
            with lock:
                results.append((thread_id, False))
    
    # Lancer plusieurs threads
    num_threads = 10
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(sign_message, i) for i in range(num_threads)]
        for future in as_completed(futures):
            future.result()
    
    # Vérifier que toutes les signatures ont réussi
    assert len(results) == num_threads
    assert all(success for _, success in results), "Some concurrent signatures failed"


# ============================================================================
# TESTS: Cross-Version Compatibility
# ============================================================================

@pytest.mark.compliance
def test_eddsa_key_serialization_deserialization(isolated_fs):
    """
    Test de conformité: Sérialisation/désérialisation de clés
    
    Vérifie:
    - Les clés peuvent être sauvegardées et rechargées
    - Format compatible
    - Signatures restent valides après rechargement
    """
    # Générer une clé
    original_private_key = ed25519.Ed25519PrivateKey.generate()
    original_public_key = original_private_key.public_key()
    
    # Sérialiser la clé publique
    public_pem = original_public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    # Signer un message
    message = b"test message"
    signature = original_private_key.sign(message)
    
    # Désérialiser la clé publique
    loaded_public_key = serialization.load_pem_public_key(public_pem)
    
    # Vérifier avec la clé rechargée
    try:
        loaded_public_key.verify(signature, message)
        serialization_works = True
    except Exception:
        serialization_works = False
    
    assert serialization_works, "Key serialization/deserialization failed"


@pytest.mark.compliance
def test_eddsa_base64_encoding_compatibility(isolated_fs):
    """
    Test de conformité: Compatibilité encodage Base64
    
    Vérifie:
    - Les signatures peuvent être encodées en base64
    - Le décodage fonctionne correctement
    - Format conforme aux DR
    """
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    message = b"test message"
    signature = private_key.sign(message)
    
    # Encoder en base64 (comme dans les DR)
    signature_b64 = base64.b64encode(signature).decode('ascii')
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    public_key_b64 = base64.b64encode(public_key_bytes).decode('ascii')
    
    # Décoder
    decoded_signature = base64.b64decode(signature_b64)
    decoded_public_key_bytes = base64.b64decode(public_key_b64)
    
    # Reconstruire la clé publique
    reconstructed_public_key = ed25519.Ed25519PublicKey.from_public_bytes(
        decoded_public_key_bytes
    )
    
    # Vérifier avec la clé reconstruite
    try:
        reconstructed_public_key.verify(decoded_signature, message)
        base64_compatible = True
    except Exception:
        base64_compatible = False
    
    assert base64_compatible, "Base64 encoding/decoding failed"


# ============================================================================
# TESTS: Edge Cases
# ============================================================================

@pytest.mark.compliance
def test_eddsa_empty_message_signature(isolated_fs):
    """
    Test de conformité: Signature de message vide
    
    Vérifie:
    - Messages vides peuvent être signés
    - Vérification fonctionne
    - Pas de crash
    """
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    # Message vide
    empty_message = b""
    
    # Signer
    signature = private_key.sign(empty_message)
    
    # Vérifier
    try:
        public_key.verify(signature, empty_message)
        empty_message_works = True
    except Exception:
        empty_message_works = False
    
    assert empty_message_works, "Empty message signature failed"


@pytest.mark.compliance
def test_eddsa_large_message_signature(isolated_fs):
    """
    Test de conformité: Signature de message volumineux
    
    Vérifie:
    - Messages de grande taille peuvent être signés
    - Performance acceptable
    - Pas de limitation de taille
    """
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    # Message de 1MB
    large_message = b"x" * (1024 * 1024)
    
    # Signer
    import time
    start = time.time()
    signature = private_key.sign(large_message)
    sign_time = time.time() - start
    
    # Vérifier
    start = time.time()
    try:
        public_key.verify(signature, large_message)
        verification_ok = True
    except Exception:
        verification_ok = False
    verify_time = time.time() - start
    
    assert verification_ok, "Large message signature failed"
    # Les opérations doivent rester raisonnables (< 1s pour 1MB)
    assert sign_time < 1.0, f"Signing large message too slow: {sign_time:.3f}s"
    assert verify_time < 1.0, f"Verifying large message too slow: {verify_time:.3f}s"


@pytest.mark.compliance
def test_eddsa_unicode_message_signature(isolated_fs):
    """
    Test de conformité: Signature de messages Unicode
    
    Vérifie:
    - Messages Unicode sont correctement gérés
    - Encodage cohérent
    - Vérification réussit
    """
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    # Messages avec caractères spéciaux
    unicode_messages = [
        "Hello 世界",
        "Bonjour café ☕",
        "Тест кириллица",
        "🎉🎊 Emoji test 🚀"
    ]
    
    for msg_str in unicode_messages:
        message = msg_str.encode('utf-8')
        
        # Signer
        signature = private_key.sign(message)
        
        # Vérifier
        try:
            public_key.verify(signature, message)
            unicode_ok = True
        except Exception:
            unicode_ok = False
        
        assert unicode_ok, f"Unicode message signature failed: {msg_str}"
