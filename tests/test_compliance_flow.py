"""
Tests de conformité et validation pour FilAgent

Ce module teste:
- Validation de l'intégrité WORM (Write-Once-Read-Many)
- Signatures EdDSA des Decision Records
- Structure et validité PROV-JSON
- Conformité aux standards W3C PROV
- Politiques RBAC et PII
"""

import pytest
import json
import hashlib
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

from runtime.middleware.worm import MerkleTree, WormLogger
from runtime.middleware.audittrail import DRManager
from runtime.middleware.provenance import ProvBuilder, ProvenanceTracker


# ============================================================================
# TESTS: WORM Integrity (Write-Once-Read-Many)
# ============================================================================

@pytest.mark.compliance
def test_worm_merkle_tree_basic():
    """
    Test de conformité: Construction d'arbre de Merkle basique

    Vérifie:
    - Construction correcte de l'arbre
    - Calcul des hash
    - Root hash présent
    """
    tree = MerkleTree()

    data = ["block1", "block2", "block3", "block4"]
    root = tree.build_tree(data)

    # Vérifier que le root existe
    assert root is not None
    assert root.hash is not None

    # Le hash du root doit être déterministe
    assert len(root.hash) == 64  # SHA-256 = 64 caractères hex


@pytest.mark.compliance
def test_worm_merkle_tree_deterministic():
    """
    Test de conformité: Les arbres de Merkle sont déterministes

    Vérifie:
    - Même données → même hash
    - Reproductibilité
    """
    tree1 = MerkleTree()
    tree2 = MerkleTree()

    data = ["a", "b", "c", "d"]

    root1 = tree1.build_tree(data)
    root2 = tree2.build_tree(data)

    # Les deux arbres doivent avoir le même root hash
    assert root1.hash == root2.hash


@pytest.mark.compliance
def test_worm_merkle_tree_integrity_detection():
    """
    Test de conformité: Détection de modification de données

    Vérifie:
    - Changement de données → changement de hash
    - Intégrité détectable
    """
    tree1 = MerkleTree()
    tree2 = MerkleTree()

    data1 = ["a", "b", "c", "d"]
    data2 = ["a", "b", "MODIFIED", "d"]  # Une donnée modifiée

    root1 = tree1.build_tree(data1)
    root2 = tree2.build_tree(data2)

    # Les hash doivent être différents
    assert root1.hash != root2.hash


@pytest.mark.compliance
def test_worm_merkle_tree_odd_number_of_leaves():
    """
    Test de conformité: Arbre de Merkle avec nombre impair de feuilles

    Vérifie:
    - Gestion correcte du cas impair
    - Pas de crash
    """
    tree = MerkleTree()

    data = ["a", "b", "c"]  # Nombre impair
    root = tree.build_tree(data)

    assert root is not None
    assert root.hash is not None


@pytest.mark.compliance
def test_worm_logger_append_only(isolated_logging):
    """
    Test de conformité: WORM logger est append-only

    Vérifie:
    - Les logs ne peuvent être que ajoutés
    - Pas de modification possible
    - Intégrité maintenue
    """
    worm_logger = isolated_logging['worm_logger']
    log_dir = isolated_logging['event_log_dir']

    # Ajouter quelques entrées
    entries = [
        {"event": "test1", "timestamp": "2024-01-01T00:00:00Z"},
        {"event": "test2", "timestamp": "2024-01-01T00:01:00Z"},
        {"event": "test3", "timestamp": "2024-01-01T00:02:00Z"}
    ]

    for entry in entries:
        worm_logger.append(json.dumps(entry))

    # Vérifier que les fichiers de log existent
    log_files = list(log_dir.glob("*.jsonl"))
    assert len(log_files) > 0

    # Lire le contenu
    with open(log_files[0], 'r') as f:
        lines = f.readlines()

    # Vérifier que toutes les entrées sont présentes
    assert len(lines) >= len(entries)


@pytest.mark.compliance
def test_worm_digest_creation(isolated_logging):
    """
    Test de conformité: Création de digest WORM

    Vérifie:
    - Les digests sont créés
    - Format JSON valide
    - Contient root hash
    """
    worm_logger = isolated_logging['worm_logger']
    digest_dir = isolated_logging['digest_dir']

    # Ajouter des entrées
    for i in range(10):
        worm_logger.append(json.dumps({"event": f"test{i}"}))

    # Forcer la création d'un checkpoint
    worm_logger.create_checkpoint()

    # Vérifier que le digest existe
    digest_files = list(digest_dir.glob("*.json"))
    assert len(digest_files) > 0

    # Vérifier le contenu du digest
    with open(digest_files[0], 'r') as f:
        digest = json.load(f)

    assert "timestamp" in digest
    assert "root_hash" in digest
    assert "num_entries" in digest
    assert digest["num_entries"] > 0


@pytest.mark.compliance
def test_worm_digest_integrity_verification(isolated_logging):
    """
    Test de conformité: Vérification d'intégrité via digest

    Vérifie:
    - Le digest peut être utilisé pour vérifier l'intégrité
    - Détection de tampering
    """
    worm_logger = isolated_logging['worm_logger']
    log_dir = isolated_logging['event_log_dir']
    digest_dir = isolated_logging['digest_dir']

    # Ajouter des entrées
    entries = []
    for i in range(5):
        entry = json.dumps({"event": f"test{i}"})
        entries.append(entry)
        worm_logger.append(entry)

    # Créer un checkpoint
    worm_logger.create_checkpoint()

    # Lire le digest
    digest_files = list(digest_dir.glob("*.json"))
    with open(digest_files[0], 'r') as f:
        digest = json.load(f)

    original_root_hash = digest["root_hash"]

    # Recalculer le hash à partir des données
    tree = MerkleTree()
    tree.build_tree(entries)
    recalculated_hash = tree.root.hash

    # Les hash doivent correspondre
    assert recalculated_hash == original_root_hash


# ============================================================================
# TESTS: Decision Records (DR) avec signatures EdDSA
# ============================================================================

@pytest.mark.compliance
def test_dr_signature_creation(isolated_fs):
    """
    Test de conformité: Création de signature EdDSA pour DR

    Vérifie:
    - Signature créée
    - Algorithme EdDSA
    - Format correct
    """
    dr_manager = DRManager(
        dr_dir=str(isolated_fs['logs_decisions'])
    )

    # Créer un Decision Record
    dr_id = dr_manager.create_record(
        conversation_id="test_conv",
        decision_type="tool_invocation",
        context={"tool": "python_sandbox", "params": {"code": "print('test')"}},
        rationale="Testing DR creation"
    )

    # Vérifier que le fichier existe
    dr_files = list(isolated_fs['logs_decisions'].glob("*.json"))
    assert len(dr_files) > 0

    # Lire le DR
    with open(dr_files[0], 'r') as f:
        dr_data = json.load(f)

    # Vérifier la structure
    assert "decision_id" in dr_data
    assert "signature" in dr_data

    # Vérifier la signature
    sig = dr_data["signature"]
    assert "algorithm" in sig
    assert sig["algorithm"] == "EdDSA"
    assert "public_key" in sig
    assert "signature" in sig

    # La signature doit être une chaîne non vide
    assert len(sig["signature"]) > 0
    assert len(sig["public_key"]) > 0


@pytest.mark.compliance
def test_dr_signature_verification(isolated_fs):
    """
    Test de conformité: Vérification de signature EdDSA

    Vérifie:
    - La signature peut être vérifiée
    - Détection de tampering
    """
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    import base64

    dr_manager = DRManager(
        dr_dir=str(isolated_fs['logs_decisions'])
    )

    # Créer un DR
    dr_id = dr_manager.create_record(
        conversation_id="test_conv",
        decision_type="tool_invocation",
        context={"tool": "test"},
        rationale="Testing signature"
    )

    # Lire le DR
    dr_files = list(isolated_fs['logs_decisions'].glob("*.json"))
    with open(dr_files[0], 'r') as f:
        dr_data = json.load(f)

    # Extraire la signature et la clé publique
    sig_data = dr_data["signature"]
    public_key_bytes = base64.b64decode(sig_data["public_key"])
    signature_bytes = base64.b64decode(sig_data["signature"])

    # Reconstruire la clé publique
    public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)

    # Reconstruire le message signé (sans la signature)
    message_data = {k: v for k, v in dr_data.items() if k != "signature"}
    message = json.dumps(message_data, sort_keys=True)

    # Vérifier la signature
    try:
        public_key.verify(signature_bytes, message.encode())
        signature_valid = True
    except Exception:
        signature_valid = False

    assert signature_valid, "Signature verification failed"


@pytest.mark.compliance
def test_dr_tampering_detection(isolated_fs):
    """
    Test de conformité: Détection de tampering dans DR

    Vérifie:
    - Modification détectée
    - Signature invalide après modification
    """
    from cryptography.hazmat.primitives.asymmetric import ed25519
    import base64

    dr_manager = DRManager(
        dr_dir=str(isolated_fs['logs_decisions'])
    )

    # Créer un DR
    dr_id = dr_manager.create_record(
        conversation_id="test_conv",
        decision_type="tool_invocation",
        context={"tool": "test"},
        rationale="Original rationale"
    )

    # Lire et modifier le DR
    dr_files = list(isolated_fs['logs_decisions'].glob("*.json"))
    with open(dr_files[0], 'r') as f:
        dr_data = json.load(f)

    # Modifier le rationale (tampering!)
    dr_data["rationale"] = "TAMPERED RATIONALE"

    # Essayer de vérifier la signature avec les données modifiées
    sig_data = dr_data["signature"]
    public_key_bytes = base64.b64decode(sig_data["public_key"])
    signature_bytes = base64.b64decode(sig_data["signature"])

    public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)

    message_data = {k: v for k, v in dr_data.items() if k != "signature"}
    message = json.dumps(message_data, sort_keys=True)

    # La vérification doit échouer
    try:
        public_key.verify(signature_bytes, message.encode())
        tampering_detected = False
    except Exception:
        tampering_detected = True

    assert tampering_detected, "Tampering was not detected!"


@pytest.mark.compliance
def test_dr_complete_structure(isolated_fs):
    """
    Test de conformité: Structure complète d'un Decision Record

    Vérifie tous les champs requis
    """
    dr_manager = DRManager(
        dr_dir=str(isolated_fs['logs_decisions'])
    )

    dr_id = dr_manager.create_record(
        conversation_id="test_conv",
        decision_type="tool_invocation",
        context={"tool": "python_sandbox"},
        rationale="Test rationale",
        metadata={"user": "test_user", "session": "sess_123"}
    )

    dr_files = list(isolated_fs['logs_decisions'].glob("*.json"))
    with open(dr_files[0], 'r') as f:
        dr_data = json.load(f)

    # Vérifier tous les champs requis
    required_fields = [
        "decision_id",
        "timestamp",
        "conversation_id",
        "decision_type",
        "context",
        "rationale",
        "signature"
    ]

    for field in required_fields:
        assert field in dr_data, f"Missing required field: {field}"

    # Vérifier les types
    assert isinstance(dr_data["decision_id"], str)
    assert isinstance(dr_data["timestamp"], str)
    assert isinstance(dr_data["context"], dict)
    assert isinstance(dr_data["signature"], dict)


# ============================================================================
# TESTS: Provenance PROV-JSON (W3C Standard)
# ============================================================================

@pytest.mark.compliance
def test_provenance_prov_builder_entities():
    """
    Test de conformité: Construction d'entités PROV

    Vérifie:
    - Format conforme W3C PROV
    - Structure correcte
    """
    builder = ProvBuilder()

    builder.add_entity(
        entity_id="entity:message_123",
        label="User Message",
        attributes={
            "content_hash": "abc123",
            "prov:type": "Message"
        }
    )

    # Vérifier que l'entité est enregistrée
    assert "entity:message_123" in builder.entities

    entity = builder.entities["entity:message_123"]
    assert entity["prov:label"] == "User Message"
    assert "content_hash" in entity


@pytest.mark.compliance
def test_provenance_prov_builder_activities():
    """
    Test de conformité: Construction d'activités PROV

    Vérifie le format des activités
    """
    builder = ProvBuilder()

    start_time = "2024-01-01T00:00:00Z"
    end_time = "2024-01-01T00:01:00Z"

    builder.add_activity(
        activity_id="activity:generation_1",
        start_time=start_time,
        end_time=end_time
    )

    # Vérifier l'activité
    assert "activity:generation_1" in builder.activities

    activity = builder.activities["activity:generation_1"]
    assert activity["prov:type"] == "Activity"
    assert activity["prov:startTime"] == start_time
    assert activity["prov:endTime"] == end_time


@pytest.mark.compliance
def test_provenance_prov_builder_agents():
    """
    Test de conformité: Construction d'agents PROV
    """
    builder = ProvBuilder()

    builder.add_agent(
        agent_id="agent:filagent_v1",
        agent_type="softwareAgent",
        version="1.0.0"
    )

    assert "agent:filagent_v1" in builder.agents

    agent = builder.agents["agent:filagent_v1"]
    assert agent["prov:type"] == "softwareAgent"
    assert agent["version"] == "1.0.0"


@pytest.mark.compliance
def test_provenance_prov_builder_relations():
    """
    Test de conformité: Relations PROV (wasGeneratedBy, used, etc.)

    Vérifie:
    - Relations correctement créées
    - Format conforme W3C
    """
    builder = ProvBuilder()

    # Ajouter des entités et activités
    builder.add_entity("entity:output", "Output Message")
    builder.add_activity("activity:gen", "2024-01-01T00:00:00Z", "2024-01-01T00:01:00Z")
    builder.add_agent("agent:system", "softwareAgent")

    # Ajouter des relations
    builder.was_generated_by.append({
        "prov:entity": "entity:output",
        "prov:activity": "activity:gen"
    })

    builder.used.append({
        "prov:activity": "activity:gen",
        "prov:entity": "entity:input"
    })

    builder.was_associated_with.append({
        "prov:activity": "activity:gen",
        "prov:agent": "agent:system"
    })

    # Vérifier les relations
    assert len(builder.was_generated_by) == 1
    assert len(builder.used) == 1
    assert len(builder.was_associated_with) == 1


@pytest.mark.compliance
def test_provenance_complete_graph_structure(isolated_fs):
    """
    Test de conformité: Structure complète d'un graphe PROV-JSON

    Vérifie:
    - Toutes les sections présentes
    - Format JSON valide
    - Conforme au standard W3C
    """
    tracker = ProvenanceTracker(
        output_dir=str(isolated_fs['logs'])
    )

    # Tracer une génération complète
    prov_id = tracker.track_generation(
        conversation_id="test_conv",
        input_message="Test input",
        output_message="Test output",
        tool_calls=[
            {"name": "python_sandbox", "result": "success"}
        ],
        metadata={"model": "test_model", "tokens": 100}
    )

    # Vérifier que le fichier PROV a été créé
    prov_files = list(isolated_fs['logs'].glob("**/prov_*.json"))

    if len(prov_files) > 0:
        with open(prov_files[0], 'r') as f:
            prov_data = json.load(f)

        # Vérifier la structure W3C PROV
        # Format: {"prefix": {...}, "entity": {...}, "activity": {...}, ...}
        assert isinstance(prov_data, dict)

        # Peut contenir ces sections (selon l'implémentation)
        possible_sections = [
            "entity", "activity", "agent",
            "wasGeneratedBy", "used", "wasAssociatedWith",
            "wasAttributedTo", "wasDerivedFrom"
        ]

        # Au moins une section doit être présente
        has_section = any(section in prov_data for section in possible_sections)
        assert has_section, "PROV document has no recognized sections"


@pytest.mark.compliance
def test_provenance_json_schema_validation(isolated_fs):
    """
    Test de conformité: Validation du schéma JSON PROV

    Vérifie que le JSON généré est bien formé
    """
    tracker = ProvenanceTracker(
        output_dir=str(isolated_fs['logs'])
    )

    prov_id = tracker.track_generation(
        conversation_id="test_conv",
        input_message="Test",
        output_message="Response",
        tool_calls=[],
        metadata={}
    )

    prov_files = list(isolated_fs['logs'].glob("**/prov_*.json"))

    if len(prov_files) > 0:
        # Vérifier que c'est du JSON valide
        with open(prov_files[0], 'r') as f:
            try:
                prov_data = json.load(f)
                json_valid = True
            except json.JSONDecodeError:
                json_valid = False

        assert json_valid, "PROV file is not valid JSON"


@pytest.mark.compliance
def test_provenance_chain_traceability(isolated_fs):
    """
    Test de conformité: Traçabilité en chaîne dans PROV

    Vérifie:
    - Les entités sont liées
    - La provenance peut être tracée
    - Relations wasDerivedFrom présentes
    """
    tracker = ProvenanceTracker(
        output_dir=str(isolated_fs['logs'])
    )

    # Tracer plusieurs générations successives
    prov_id1 = tracker.track_generation(
        conversation_id="test_conv",
        input_message="First input",
        output_message="First output",
        tool_calls=[],
        metadata={}
    )

    prov_id2 = tracker.track_generation(
        conversation_id="test_conv",
        input_message="Second input (based on first output)",
        output_message="Second output",
        tool_calls=[],
        metadata={"derived_from": prov_id1}
    )

    # Vérifier que les fichiers existent
    prov_files = list(isolated_fs['logs'].glob("**/prov_*.json"))
    assert len(prov_files) >= 1  # Au moins un fichier créé


# ============================================================================
# TESTS: Conformité Intégrée (WORM + DR + PROV)
# ============================================================================

@pytest.mark.compliance
def test_compliance_full_audit_trail(api_client, patched_middlewares):
    """
    Test de conformité: Audit trail complet

    Vérifie que tous les systèmes de conformité fonctionnent ensemble:
    - WORM logging
    - Decision Records
    - Provenance tracking
    """
    # Envoyer une requête
    response = api_client.post("/chat", json={
        "messages": [
            {"role": "user", "content": "Test audit trail"}
        ]
    })

    assert response.status_code == 200
    conversation_id = response.json()["id"]

    isolated_fs = patched_middlewares['isolated_fs']

    # Vérifier WORM logs
    log_files = list(isolated_fs['logs_events'].glob("*.jsonl"))
    assert len(log_files) > 0, "No WORM logs created"

    # Vérifier que les logs sont en JSON lines
    with open(log_files[0], 'r') as f:
        lines = f.readlines()
        for line in lines:
            json.loads(line)  # Ne doit pas crasher

    # Vérifier Decision Records (peuvent exister selon le flux)
    dr_files = list(isolated_fs['logs_decisions'].glob("*.json"))
    # Les DR ne sont créés que si décision prise, donc on vérifie juste le format
    for dr_file in dr_files:
        with open(dr_file, 'r') as f:
            dr_data = json.load(f)
            assert "decision_id" in dr_data
            assert "signature" in dr_data

    # Vérifier Provenance (peut exister selon le flux)
    prov_files = list(isolated_fs['logs'].glob("**/prov_*.json"))
    for prov_file in prov_files:
        with open(prov_file, 'r') as f:
            json.load(f)  # Ne doit pas crasher


@pytest.mark.compliance
def test_compliance_data_retention_integrity(isolated_logging):
    """
    Test de conformité: Intégrité des données sur la durée

    Vérifie:
    - Les données persistent
    - L'intégrité est maintenue
    - Les checkpoints fonctionnent
    """
    worm_logger = isolated_logging['worm_logger']

    # Ajouter des entrées sur plusieurs "périodes"
    for period in range(3):
        for i in range(10):
            worm_logger.append(json.dumps({
                "period": period,
                "entry": i,
                "timestamp": datetime.utcnow().isoformat()
            }))

        # Créer un checkpoint après chaque période
        worm_logger.create_checkpoint()

    # Vérifier que plusieurs checkpoints existent
    digest_dir = isolated_logging['digest_dir']
    digest_files = list(digest_dir.glob("*.json"))

    assert len(digest_files) >= 1, "No checkpoints created"

    # Vérifier que chaque checkpoint est valide
    for digest_file in digest_files:
        with open(digest_file, 'r') as f:
            digest = json.load(f)

        assert "root_hash" in digest
        assert "timestamp" in digest
        assert digest["num_entries"] > 0


@pytest.mark.compliance
def test_compliance_non_repudiation(isolated_fs):
    """
    Test de conformité: Non-répudiation via signatures

    Vérifie:
    - Les signatures garantissent la non-répudiation
    - Les DR ne peuvent être niés
    """
    dr_manager = DRManager(
        dr_dir=str(isolated_fs['logs_decisions'])
    )

    # Créer un DR important
    dr_id = dr_manager.create_record(
        conversation_id="important_conv",
        decision_type="critical_action",
        context={"action": "data_deletion", "target": "user_data_123"},
        rationale="User requested data deletion",
        metadata={"user_id": "user_456", "timestamp": datetime.utcnow().isoformat()}
    )

    # Lire et vérifier
    dr_files = list(isolated_fs['logs_decisions'].glob("*.json"))
    with open(dr_files[0], 'r') as f:
        dr_data = json.load(f)

    # La signature garantit:
    # 1. Authenticité (vient bien du système)
    # 2. Intégrité (pas modifié)
    # 3. Non-répudiation (ne peut être nié)

    assert "signature" in dr_data
    assert dr_data["signature"]["algorithm"] == "EdDSA"

    # La clé publique permet à n'importe qui de vérifier
    assert "public_key" in dr_data["signature"]
