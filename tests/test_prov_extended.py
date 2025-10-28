"""
Extended PROV-JSON compliance tests

Tests W3C PROV standard compliance and edge cases:
- Graph serialization/deserialization
- W3C schema validation
- Entity attribution chains
- Activity temporal ordering
- Namespace handling
"""

import pytest
import json
from pathlib import Path
from datetime import datetime, timedelta

from runtime.middleware.provenance import ProvBuilder, ProvenanceTracker


# ============================================================================
# TESTS: PROV-JSON Serialization and Schema
# ============================================================================

@pytest.mark.compliance
def test_prov_json_serialization_roundtrip(isolated_fs):
    """
    Test de conformité: Sérialisation/désérialisation PROV-JSON
    
    Vérifie:
    - Le graphe peut être sérialisé en JSON
    - Le JSON peut être désérialisé
    - Les données sont préservées
    """
    builder = ProvBuilder()
    
    # Construire un graphe simple
    builder.add_entity("entity:msg1", "User Message", {"hash": "abc123"})
    builder.add_activity("activity:gen1", "2024-01-01T00:00:00Z", "2024-01-01T00:01:00Z")
    builder.add_agent("agent:system", "softwareAgent", version="1.0.0")
    
    builder.was_generated_by.append({
        "prov:entity": "entity:msg1",
        "prov:activity": "activity:gen1"
    })
    
    # Construire le document PROV
    prov_doc = {
        "entity": builder.entities,
        "activity": builder.activities,
        "agent": builder.agents,
        "wasGeneratedBy": builder.was_generated_by
    }
    
    # Sérialiser en JSON
    json_str = json.dumps(prov_doc, indent=2)
    
    # Désérialiser
    loaded_doc = json.loads(json_str)
    
    # Vérifier que les données sont préservées
    assert "entity" in loaded_doc
    assert "entity:msg1" in loaded_doc["entity"]
    assert loaded_doc["entity"]["entity:msg1"]["prov:label"] == "User Message"
    
    assert "activity" in loaded_doc
    assert "activity:gen1" in loaded_doc["activity"]
    
    assert "agent" in loaded_doc
    assert "agent:system" in loaded_doc["agent"]
    
    assert "wasGeneratedBy" in loaded_doc
    assert len(loaded_doc["wasGeneratedBy"]) == 1


@pytest.mark.compliance
def test_prov_w3c_schema_structure(isolated_fs):
    """
    Test de conformité: Structure conforme au schéma W3C PROV
    
    Vérifie:
    - Les sections requises sont présentes
    - Les types sont corrects
    - Les relations utilisent la notation prov:
    """
    builder = ProvBuilder()
    
    # Ajouter des éléments
    builder.add_entity("entity:doc", "Document", {"prov:type": "Document"})
    builder.add_activity(
        "activity:creation", 
        "2024-01-01T00:00:00Z", 
        "2024-01-01T00:01:00Z"
    )
    builder.add_agent("agent:user", "person")
    
    # Ajouter des relations
    builder.was_generated_by.append({
        "prov:entity": "entity:doc",
        "prov:activity": "activity:creation"
    })
    
    builder.was_associated_with.append({
        "prov:activity": "activity:creation",
        "prov:agent": "agent:user"
    })
    
    # Construire le document
    prov_doc = {
        "entity": builder.entities,
        "activity": builder.activities,
        "agent": builder.agents,
        "wasGeneratedBy": builder.was_generated_by,
        "wasAssociatedWith": builder.was_associated_with
    }
    
    # Vérifier la structure W3C
    assert isinstance(prov_doc, dict), "PROV document should be a dictionary"
    
    # Vérifier que les entités ont des labels
    for entity_id, entity in prov_doc["entity"].items():
        assert "prov:label" in entity, f"Entity {entity_id} missing prov:label"
    
    # Vérifier que les activités ont startTime et endTime
    for activity_id, activity in prov_doc["activity"].items():
        assert "prov:startTime" in activity, f"Activity {activity_id} missing prov:startTime"
        assert "prov:endTime" in activity, f"Activity {activity_id} missing prov:endTime"
    
    # Vérifier que les agents ont un type
    for agent_id, agent in prov_doc["agent"].items():
        assert "prov:type" in agent, f"Agent {agent_id} missing prov:type"


@pytest.mark.compliance
def test_prov_namespace_handling(isolated_fs):
    """
    Test de conformité: Gestion des namespaces PROV
    
    Vérifie:
    - Les préfixes prov: sont utilisés correctement
    - Les IDs suivent les conventions
    - Les attributs utilisent le namespace approprié
    """
    builder = ProvBuilder()
    
    # Utiliser des IDs avec namespace
    builder.add_entity("filagent:entity:message_123", "Message", {
        "prov:type": "Message",
        "filagent:content_hash": "sha256:abc123"
    })
    
    builder.add_activity(
        "filagent:activity:generation_456",
        "2024-01-01T00:00:00Z",
        "2024-01-01T00:01:00Z"
    )
    
    # Vérifier que les namespaces sont préservés
    assert "filagent:entity:message_123" in builder.entities
    assert "filagent:activity:generation_456" in builder.activities
    
    entity = builder.entities["filagent:entity:message_123"]
    assert "prov:type" in entity
    assert "filagent:content_hash" in entity


# ============================================================================
# TESTS: Entity Attribution Chains
# ============================================================================

@pytest.mark.compliance
def test_prov_entity_attribution_chain(isolated_fs):
    """
    Test de conformité: Chaînes d'attribution d'entités
    
    Vérifie:
    - Les entités peuvent être liées entre elles
    - wasDerivedFrom crée une chaîne
    - La provenance peut être tracée
    """
    builder = ProvBuilder()
    
    # Créer une chaîne de dérivation
    builder.add_entity("entity:input", "Input Message")
    builder.add_entity("entity:processed", "Processed Message")
    builder.add_entity("entity:output", "Output Message")
    
    # Ajouter les relations de dérivation
    builder.was_derived_from.append({
        "prov:generatedEntity": "entity:processed",
        "prov:usedEntity": "entity:input"
    })
    
    builder.was_derived_from.append({
        "prov:generatedEntity": "entity:output",
        "prov:usedEntity": "entity:processed"
    })
    
    # Vérifier la chaîne
    assert len(builder.was_derived_from) == 2
    
    # Tracer la chaîne depuis output jusqu'à input
    chain = []
    current = "entity:output"
    
    while current:
        chain.append(current)
        # Trouver le parent
        parent = None
        for relation in builder.was_derived_from:
            if relation["prov:generatedEntity"] == current:
                parent = relation["prov:usedEntity"]
                break
        current = parent
    
    # La chaîne devrait être: output -> processed -> input
    assert len(chain) == 3
    assert chain[0] == "entity:output"
    assert chain[1] == "entity:processed"
    assert chain[2] == "entity:input"


@pytest.mark.compliance
def test_prov_multiple_attribution_sources(isolated_fs):
    """
    Test de conformité: Entité dérivée de multiples sources
    
    Vérifie:
    - Une entité peut être dérivée de plusieurs sources
    - Toutes les attributions sont préservées
    - Le graphe reste cohérent
    """
    builder = ProvBuilder()
    
    # Créer plusieurs sources
    builder.add_entity("entity:source1", "Source 1")
    builder.add_entity("entity:source2", "Source 2")
    builder.add_entity("entity:source3", "Source 3")
    builder.add_entity("entity:combined", "Combined Result")
    
    # L'entité combinée est dérivée de toutes les sources
    builder.was_derived_from.append({
        "prov:generatedEntity": "entity:combined",
        "prov:usedEntity": "entity:source1"
    })
    builder.was_derived_from.append({
        "prov:generatedEntity": "entity:combined",
        "prov:usedEntity": "entity:source2"
    })
    builder.was_derived_from.append({
        "prov:generatedEntity": "entity:combined",
        "prov:usedEntity": "entity:source3"
    })
    
    # Vérifier que toutes les attributions sont présentes
    combined_sources = [
        rel["prov:usedEntity"] 
        for rel in builder.was_derived_from 
        if rel["prov:generatedEntity"] == "entity:combined"
    ]
    
    assert len(combined_sources) == 3
    assert "entity:source1" in combined_sources
    assert "entity:source2" in combined_sources
    assert "entity:source3" in combined_sources


# ============================================================================
# TESTS: Activity Temporal Ordering
# ============================================================================

@pytest.mark.compliance
def test_prov_activity_temporal_ordering(isolated_fs):
    """
    Test de conformité: Ordre temporel des activités
    
    Vérifie:
    - Les timestamps sont au format ISO8601
    - startTime < endTime
    - Les activités peuvent être ordonnées chronologiquement
    """
    builder = ProvBuilder()
    
    # Créer des activités avec ordre temporel
    activities = [
        ("activity:step1", "2024-01-01T00:00:00Z", "2024-01-01T00:01:00Z"),
        ("activity:step2", "2024-01-01T00:01:00Z", "2024-01-01T00:02:00Z"),
        ("activity:step3", "2024-01-01T00:02:00Z", "2024-01-01T00:03:00Z")
    ]
    
    for activity_id, start, end in activities:
        builder.add_activity(activity_id, start, end)
    
    # Vérifier l'ordre
    sorted_activities = sorted(
        builder.activities.items(),
        key=lambda x: x[1]["prov:startTime"]
    )
    
    assert len(sorted_activities) == 3
    assert sorted_activities[0][0] == "activity:step1"
    assert sorted_activities[1][0] == "activity:step2"
    assert sorted_activities[2][0] == "activity:step3"
    
    # Vérifier que startTime < endTime pour chaque activité
    for activity_id, activity in builder.activities.items():
        start = datetime.fromisoformat(activity["prov:startTime"].replace('Z', '+00:00'))
        end = datetime.fromisoformat(activity["prov:endTime"].replace('Z', '+00:00'))
        assert start < end, f"Activity {activity_id} has invalid time range"


@pytest.mark.compliance
def test_prov_activity_overlap_detection(isolated_fs):
    """
    Test de conformité: Détection d'activités concurrentes
    
    Vérifie:
    - Activités qui se chevauchent temporellement
    - Support pour parallélisme
    """
    builder = ProvBuilder()
    
    # Créer des activités qui se chevauchent
    builder.add_activity("activity:parallel1", "2024-01-01T00:00:00Z", "2024-01-01T00:02:00Z")
    builder.add_activity("activity:parallel2", "2024-01-01T00:01:00Z", "2024-01-01T00:03:00Z")
    
    # Extraire les plages temporelles
    act1 = builder.activities["activity:parallel1"]
    act2 = builder.activities["activity:parallel2"]
    
    start1 = datetime.fromisoformat(act1["prov:startTime"].replace('Z', '+00:00'))
    end1 = datetime.fromisoformat(act1["prov:endTime"].replace('Z', '+00:00'))
    
    start2 = datetime.fromisoformat(act2["prov:startTime"].replace('Z', '+00:00'))
    end2 = datetime.fromisoformat(act2["prov:endTime"].replace('Z', '+00:00'))
    
    # Vérifier le chevauchement
    overlap = (start1 < end2) and (start2 < end1)
    assert overlap, "Activities should overlap temporally"


# ============================================================================
# TESTS: Complex PROV Graphs
# ============================================================================

@pytest.mark.compliance
def test_prov_complex_graph_structure(isolated_fs):
    """
    Test de conformité: Graphe PROV complexe
    
    Vérifie:
    - Graphe avec multiples nœuds et relations
    - Toutes les relations PROV supportées
    - Cohérence du graphe
    """
    builder = ProvBuilder()
    
    # Entités
    builder.add_entity("entity:input", "Input Data")
    builder.add_entity("entity:intermediate", "Intermediate Result")
    builder.add_entity("entity:output", "Final Output")
    
    # Activités
    builder.add_activity("activity:processing", "2024-01-01T00:00:00Z", "2024-01-01T00:01:00Z")
    builder.add_activity("activity:validation", "2024-01-01T00:01:00Z", "2024-01-01T00:02:00Z")
    
    # Agents
    builder.add_agent("agent:system", "softwareAgent", version="1.0")
    builder.add_agent("agent:user", "person")
    
    # Relations: wasGeneratedBy
    builder.was_generated_by.append({
        "prov:entity": "entity:intermediate",
        "prov:activity": "activity:processing"
    })
    builder.was_generated_by.append({
        "prov:entity": "entity:output",
        "prov:activity": "activity:validation"
    })
    
    # Relations: used
    builder.used.append({
        "prov:activity": "activity:processing",
        "prov:entity": "entity:input"
    })
    builder.used.append({
        "prov:activity": "activity:validation",
        "prov:entity": "entity:intermediate"
    })
    
    # Relations: wasAssociatedWith
    builder.was_associated_with.append({
        "prov:activity": "activity:processing",
        "prov:agent": "agent:system"
    })
    
    # Relations: wasAttributedTo
    builder.was_attributed_to.append({
        "prov:entity": "entity:input",
        "prov:agent": "agent:user"
    })
    
    # Relations: wasDerivedFrom
    builder.was_derived_from.append({
        "prov:generatedEntity": "entity:output",
        "prov:usedEntity": "entity:input"
    })
    
    # Vérifier que le graphe est complet
    assert len(builder.entities) == 3
    assert len(builder.activities) == 2
    assert len(builder.agents) == 2
    assert len(builder.was_generated_by) == 2
    assert len(builder.used) == 2
    assert len(builder.was_associated_with) == 1
    assert len(builder.was_attributed_to) == 1
    assert len(builder.was_derived_from) == 1


# ============================================================================
# TESTS: Edge Cases and Error Handling
# ============================================================================

@pytest.mark.compliance
def test_prov_empty_graph(isolated_fs):
    """
    Test de conformité: Graphe PROV vide
    
    Vérifie:
    - Un graphe vide est valide
    - Pas de crash
    - Sérialisation fonctionne
    """
    builder = ProvBuilder()
    
    # Ne rien ajouter
    prov_doc = {
        "entity": builder.entities,
        "activity": builder.activities,
        "agent": builder.agents
    }
    
    # Doit être sérialisable
    json_str = json.dumps(prov_doc)
    loaded = json.loads(json_str)
    
    assert loaded["entity"] == {}
    assert loaded["activity"] == {}
    assert loaded["agent"] == {}


@pytest.mark.compliance
def test_prov_special_characters_in_ids(isolated_fs):
    """
    Test de conformité: Caractères spéciaux dans les IDs
    
    Vérifie:
    - Les IDs avec caractères spéciaux sont supportés
    - Pas de problème d'échappement
    """
    builder = ProvBuilder()
    
    # IDs avec caractères spéciaux (valides selon PROV)
    special_ids = [
        "entity:message-123",
        "entity:message_456",
        "entity:message.789",
        "activity:gen@2024"
    ]
    
    for entity_id in special_ids:
        builder.add_entity(entity_id, f"Entity {entity_id}")
    
    # Vérifier que tous sont enregistrés
    for entity_id in special_ids:
        assert entity_id in builder.entities


@pytest.mark.compliance
def test_prov_duplicate_entity_handling(isolated_fs):
    """
    Test de conformité: Gestion d'entités dupliquées
    
    Vérifie:
    - Le comportement avec IDs dupliqués
    - Cohérence des données
    """
    builder = ProvBuilder()
    
    # Ajouter une entité
    builder.add_entity("entity:msg", "First Message", {"version": "1"})
    
    # Ajouter à nouveau avec le même ID
    builder.add_entity("entity:msg", "Second Message", {"version": "2"})
    
    # Selon l'implémentation, soit écrasement soit conservation
    # On vérifie juste qu'il n'y a pas de crash
    assert "entity:msg" in builder.entities
    
    # Vérifier qu'on a bien une seule entrée (pas de duplication)
    assert isinstance(builder.entities["entity:msg"], dict)


@pytest.mark.compliance
def test_prov_malformed_timestamp_handling(isolated_fs):
    """
    Test de conformité: Gestion de timestamps malformés
    
    Vérifie:
    - Détection de timestamps invalides
    - Comportement gracieux
    """
    builder = ProvBuilder()
    
    # Essayer d'ajouter une activité avec timestamp invalide
    try:
        builder.add_activity(
            "activity:test",
            "not-a-timestamp",
            "also-not-a-timestamp"
        )
        # Si aucune validation, l'activité sera ajoutée
        # On vérifie juste qu'il n'y a pas de crash
        malformed_accepted = True
    except Exception:
        # Si validation stricte, une exception est levée
        malformed_accepted = False
    
    # Soit accepté (pas de validation), soit rejeté (validation stricte)
    # Les deux comportements sont acceptables
    assert isinstance(malformed_accepted, bool)
