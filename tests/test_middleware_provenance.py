"""
Comprehensive unit tests for provenance middleware (W3C PROV-JSON)

Tests cover:
- ProvBuilder functionality
- PROV-JSON graph construction
- Entity, activity, and agent creation
- Relationship linking (wasGeneratedBy, used, etc.)
- ProvenanceTracker initialization and graceful fallbacks
- Generation tracking (new and legacy API)
- Tool execution tracking
- W3C PROV compliance
- Error handling and edge cases
"""

import json
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

from runtime.middleware.provenance import ProvBuilder, ProvenanceTracker, get_tracker, init_tracker


@pytest.fixture
def temp_prov_dir(tmp_path):
    """Temporary directory for provenance traces"""
    prov_dir = tmp_path / "logs" / "traces" / "otlp"
    prov_dir.mkdir(parents=True, exist_ok=True)
    return prov_dir


@pytest.fixture
def prov_builder():
    """Fresh ProvBuilder instance"""
    return ProvBuilder()


class TestProvBuilderInitialization:
    """Test ProvBuilder initialization"""

    def test_basic_initialization(self):
        """Test initialisation basique"""
        builder = ProvBuilder()

        assert builder.entities == {}
        assert builder.activities == {}
        assert builder.agents == {}
        assert builder.was_generated_by == []
        assert builder.was_attributed_to == []
        assert builder.used == []
        assert builder.was_associated_with == []
        assert builder.was_derived_from == []


class TestProvBuilderEntities:
    """Test entity creation and management"""

    def test_add_entity_basic(self, prov_builder):
        """Test ajout d'entité basique"""
        prov_builder.add_entity(entity_id="entity:1", label="Test Entity")

        assert "entity:1" in prov_builder.entities
        assert prov_builder.entities["entity:1"]["prov:label"] == "Test Entity"

    def test_add_entity_with_attributes(self, prov_builder):
        """Test ajout d'entité avec attributs"""
        prov_builder.add_entity(
            entity_id="entity:1",
            label="Test Entity",
            attributes={"hash": "sha256:abc123", "type": "response"},
        )

        entity = prov_builder.entities["entity:1"]
        assert entity["prov:label"] == "Test Entity"
        assert entity["hash"] == "sha256:abc123"
        assert entity["type"] == "response"

    def test_add_multiple_entities(self, prov_builder):
        """Test ajout de plusieurs entités"""
        prov_builder.add_entity("entity:1", "Entity 1")
        prov_builder.add_entity("entity:2", "Entity 2")
        prov_builder.add_entity("entity:3", "Entity 3")

        assert len(prov_builder.entities) == 3
        assert "entity:1" in prov_builder.entities
        assert "entity:2" in prov_builder.entities
        assert "entity:3" in prov_builder.entities


class TestProvBuilderActivities:
    """Test activity creation and management"""

    def test_add_activity_basic(self, prov_builder):
        """Test ajout d'activité basique"""
        start_time = "2025-01-01T00:00:00"
        end_time = "2025-01-01T00:01:00"

        prov_builder.add_activity(
            activity_id="activity:1", start_time=start_time, end_time=end_time
        )

        assert "activity:1" in prov_builder.activities
        activity = prov_builder.activities["activity:1"]
        assert activity["prov:type"] == "Activity"
        assert activity["prov:startTime"] == start_time
        assert activity["prov:endTime"] == end_time

    def test_add_multiple_activities(self, prov_builder):
        """Test ajout de plusieurs activités"""
        for i in range(3):
            prov_builder.add_activity(
                activity_id=f"activity:{i}",
                start_time=f"2025-01-01T00:0{i}:00",
                end_time=f"2025-01-01T00:0{i+1}:00",
            )

        assert len(prov_builder.activities) == 3


class TestProvBuilderAgents:
    """Test agent creation and management"""

    def test_add_agent_basic(self, prov_builder):
        """Test ajout d'agent basique"""
        prov_builder.add_agent(agent_id="agent:filagent", agent_type="softwareAgent")

        assert "agent:filagent" in prov_builder.agents
        agent = prov_builder.agents["agent:filagent"]
        assert agent["prov:type"] == "softwareAgent"

    def test_add_agent_with_version(self, prov_builder):
        """Test ajout d'agent avec version"""
        prov_builder.add_agent(
            agent_id="agent:filagent", agent_type="softwareAgent", version="1.0.0"
        )

        agent = prov_builder.agents["agent:filagent"]
        assert agent["version"] == "1.0.0"

    def test_add_different_agent_types(self, prov_builder):
        """Test différents types d'agents"""
        prov_builder.add_agent("agent:1", "softwareAgent")
        prov_builder.add_agent("agent:2", "person")
        prov_builder.add_agent("agent:3", "organization")

        assert prov_builder.agents["agent:1"]["prov:type"] == "softwareAgent"
        assert prov_builder.agents["agent:2"]["prov:type"] == "person"
        assert prov_builder.agents["agent:3"]["prov:type"] == "organization"


class TestProvBuilderRelationships:
    """Test PROV relationship linking"""

    def test_link_generated(self, prov_builder):
        """Test wasGeneratedBy relationship"""
        prov_builder.link_generated("entity:1", "activity:1")

        assert len(prov_builder.was_generated_by) == 1
        rel = prov_builder.was_generated_by[0]
        assert rel["prov:entity"] == "entity:1"
        assert rel["prov:activity"] == "activity:1"

    def test_link_associated(self, prov_builder):
        """Test wasAssociatedWith relationship"""
        prov_builder.link_associated("activity:1", "agent:1")

        assert len(prov_builder.was_associated_with) == 1
        rel = prov_builder.was_associated_with[0]
        assert rel["prov:activity"] == "activity:1"
        assert rel["prov:agent"] == "agent:1"

    def test_link_attributed(self, prov_builder):
        """Test wasAttributedTo relationship"""
        prov_builder.link_attributed("entity:1", "agent:1")

        assert len(prov_builder.was_attributed_to) == 1
        rel = prov_builder.was_attributed_to[0]
        assert rel["prov:entity"] == "entity:1"
        assert rel["prov:agent"] == "agent:1"

    def test_link_used(self, prov_builder):
        """Test used relationship"""
        prov_builder.link_used("activity:1", "entity:1")

        assert len(prov_builder.used) == 1
        rel = prov_builder.used[0]
        assert rel["prov:activity"] == "activity:1"
        assert rel["prov:entity"] == "entity:1"

    def test_link_derived(self, prov_builder):
        """Test wasDerivedFrom relationship"""
        prov_builder.link_derived("entity:2", "entity:1")

        assert len(prov_builder.was_derived_from) == 1
        rel = prov_builder.was_derived_from[0]
        assert rel["prov:generatedEntity"] == "entity:2"
        assert rel["prov:usedEntity"] == "entity:1"


class TestProvJSONSerialization:
    """Test PROV-JSON serialization"""

    def test_to_prov_json_basic(self, prov_builder):
        """Test conversion basique en PROV-JSON"""
        prov_builder.add_entity("entity:1", "Entity 1")
        prov_builder.add_activity("activity:1", "2025-01-01T00:00:00", "2025-01-01T00:01:00")
        prov_builder.add_agent("agent:1", "softwareAgent")

        prov_json = prov_builder.to_prov_json()

        assert "entity" in prov_json
        assert "activity" in prov_json
        assert "agent" in prov_json
        assert "entity:1" in prov_json["entity"]
        assert "activity:1" in prov_json["activity"]
        assert "agent:1" in prov_json["agent"]

    def test_to_prov_json_with_relationships(self, prov_builder):
        """Test PROV-JSON avec relations"""
        prov_builder.add_entity("entity:1", "Entity 1")
        prov_builder.add_activity("activity:1", "2025-01-01T00:00:00", "2025-01-01T00:01:00")
        prov_builder.add_agent("agent:1", "softwareAgent")

        prov_builder.link_generated("entity:1", "activity:1")
        prov_builder.link_associated("activity:1", "agent:1")
        prov_builder.link_used("activity:1", "entity:1")

        prov_json = prov_builder.to_prov_json()

        assert "wasGeneratedBy" in prov_json
        assert "wasAssociatedWith" in prov_json
        assert "used" in prov_json

    def test_to_prov_json_empty_relationships_excluded(self, prov_builder):
        """Test que les relations vides sont exclues"""
        prov_builder.add_entity("entity:1", "Entity 1")

        prov_json = prov_builder.to_prov_json()

        # Empty relationship lists should not be in output
        assert "wasGeneratedBy" not in prov_json
        assert "wasAssociatedWith" not in prov_json
        assert "used" not in prov_json
        assert "wasAttributedTo" not in prov_json
        assert "wasDerivedFrom" not in prov_json


class TestProvenanceTrackerInitialization:
    """Test ProvenanceTracker initialization"""

    def test_basic_initialization(self, temp_prov_dir):
        """Test initialisation basique"""
        tracker = ProvenanceTracker(storage_dir=str(temp_prov_dir))

        assert tracker.output_dir == temp_prov_dir
        assert temp_prov_dir.exists()

    def test_creates_storage_directory(self, tmp_path):
        """Test création du répertoire de stockage"""
        prov_dir = tmp_path / "non_existent" / "logs" / "traces" / "otlp"
        assert not prov_dir.exists()

        tracker = ProvenanceTracker(storage_dir=str(prov_dir))

        assert prov_dir.exists()

    def test_default_storage_directory(self):
        """Test répertoire de stockage par défaut"""
        with patch("pathlib.Path.mkdir"):
            tracker = ProvenanceTracker()
            assert "logs/traces/otlp" in str(tracker.output_dir)


class TestGenerationTrackingNewAPI:
    """Test generation tracking with new API"""

    def test_track_generation_new_api(self, temp_prov_dir):
        """Test tracking avec nouvelle API"""
        tracker = ProvenanceTracker(storage_dir=str(temp_prov_dir))

        prov_id = tracker.track_generation(
            conversation_id="conv-123",
            input_message="What is 2+2?",
            output_message="4",
            tool_calls=[{"name": "calculator", "args": {}}],
            metadata={"model": "test"},
        )

        assert prov_id.startswith("prov-conv-123-")

        # Verify file was created
        prov_files = list(temp_prov_dir.glob("prov_prov-conv-123-*.json"))
        assert len(prov_files) == 1

    def test_track_generation_creates_prov_file(self, temp_prov_dir):
        """Test création du fichier PROV-JSON"""
        tracker = ProvenanceTracker(storage_dir=str(temp_prov_dir))

        prov_id = tracker.track_generation(
            conversation_id="conv-123", input_message="Test", output_message="Response"
        )

        prov_file = temp_prov_dir / f"prov_{prov_id}.json"
        assert prov_file.exists()

        with open(prov_file, "r") as f:
            prov_data = json.load(f)

        assert "entity" in prov_data
        assert "activity" in prov_data
        assert "agent" in prov_data

    def test_track_generation_hashes_messages(self, temp_prov_dir):
        """Test hashage des messages"""
        tracker = ProvenanceTracker(storage_dir=str(temp_prov_dir))

        prov_id = tracker.track_generation(
            conversation_id="conv-123", input_message="What is 2+2?", output_message="4"
        )

        prov_file = temp_prov_dir / f"prov_{prov_id}.json"
        with open(prov_file, "r") as f:
            prov_data = json.load(f)

        # Check that entities have hashes
        entities = prov_data["entity"]
        for entity in entities.values():
            if "hash" in entity:
                assert entity["hash"].startswith("sha256:")


class TestGenerationTrackingLegacyAPI:
    """Test generation tracking with legacy API"""

    def test_track_generation_legacy_api(self, temp_prov_dir):
        """Test tracking avec API legacy"""
        tracker = ProvenanceTracker(storage_dir=str(temp_prov_dir))

        prov_id = tracker.track_generation(
            agent_id="filagent",
            agent_version="1.0.0",
            task_id="task-123",
            prompt_hash="abc123",
            response_hash="def456",
            start_time="2025-01-01T00:00:00",
            end_time="2025-01-01T00:01:00",
            metadata={"test": "data"},
        )

        assert prov_id.startswith("prov-task-123-")

        prov_file = temp_prov_dir / f"prov_{prov_id}.json"
        assert prov_file.exists()

    def test_track_generation_legacy_with_metadata(self, temp_prov_dir):
        """Test tracking legacy avec métadonnées"""
        tracker = ProvenanceTracker(storage_dir=str(temp_prov_dir))

        metadata = {"model": "test-model", "temperature": 0.7}

        prov_id = tracker.track_generation(
            agent_id="filagent",
            agent_version="1.0.0",
            task_id="task-123",
            prompt_hash="abc123",
            response_hash="def456",
            start_time="2025-01-01T00:00:00",
            end_time="2025-01-01T00:01:00",
            metadata=metadata,
        )

        prov_file = temp_prov_dir / f"prov_{prov_id}.json"
        with open(prov_file, "r") as f:
            prov_data = json.load(f)

        # Metadata should be in activity
        activities = prov_data["activity"]
        for activity in activities.values():
            if "metadata" in activity:
                assert activity["metadata"]["model"] == "test-model"


class TestToolExecutionTracking:
    """Test tool execution tracking"""

    def test_track_tool_execution(self, temp_prov_dir):
        """Test tracking d'exécution d'outil"""
        tracker = ProvenanceTracker(storage_dir=str(temp_prov_dir))

        prov_json = tracker.track_tool_execution(
            tool_name="python_sandbox",
            tool_input_hash="abc123",
            tool_output_hash="def456",
            task_id="task-123",
            start_time="2025-01-01T00:00:00",
            end_time="2025-01-01T00:01:00",
        )

        assert "entity" in prov_json
        assert "activity" in prov_json
        assert "agent" in prov_json

    def test_track_tool_execution_creates_file(self, temp_prov_dir):
        """Test création du fichier de trace d'outil"""
        tracker = ProvenanceTracker(storage_dir=str(temp_prov_dir))

        tracker.track_tool_execution(
            tool_name="calculator",
            tool_input_hash="abc123",
            tool_output_hash="def456",
            task_id="task-123",
            start_time="2025-01-01T00:00:00",
            end_time="2025-01-01T00:01:00",
        )

        prov_file = temp_prov_dir / "prov-tool-calculator-task-123.json"
        assert prov_file.exists()

    def test_track_tool_execution_relationships(self, temp_prov_dir):
        """Test relations dans le tracking d'outil"""
        tracker = ProvenanceTracker(storage_dir=str(temp_prov_dir))

        prov_json = tracker.track_tool_execution(
            tool_name="python_sandbox",
            tool_input_hash="abc123",
            tool_output_hash="def456",
            task_id="task-123",
            start_time="2025-01-01T00:00:00",
            end_time="2025-01-01T00:01:00",
        )

        # Should have wasGeneratedBy, used, and wasDerivedFrom
        assert "wasGeneratedBy" in prov_json
        assert "used" in prov_json
        assert "wasDerivedFrom" in prov_json
        assert "wasAssociatedWith" in prov_json


class TestSingletonPattern:
    """Test singleton pattern for get_tracker()"""

    def test_get_tracker_returns_singleton(self):
        """Test que get_tracker retourne toujours la même instance"""
        tracker1 = get_tracker()
        tracker2 = get_tracker()

        assert tracker1 is tracker2

    def test_init_tracker_creates_new_instance(self, temp_prov_dir):
        """Test que init_tracker crée une nouvelle instance"""
        tracker1 = init_tracker(storage_dir=str(temp_prov_dir))
        tracker2 = get_tracker()

        assert tracker1 is tracker2


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_track_generation_with_none_input(self, temp_prov_dir):
        """Test tracking avec input None"""
        tracker = ProvenanceTracker(storage_dir=str(temp_prov_dir))

        prov_id = tracker.track_generation(
            conversation_id="conv-123", input_message=None, output_message="Response"
        )

        prov_file = temp_prov_dir / f"prov_{prov_id}.json"
        assert prov_file.exists()

    def test_track_generation_with_none_output(self, temp_prov_dir):
        """Test tracking avec output None"""
        tracker = ProvenanceTracker(storage_dir=str(temp_prov_dir))

        prov_id = tracker.track_generation(
            conversation_id="conv-123", input_message="Input", output_message=None
        )

        prov_file = temp_prov_dir / f"prov_{prov_id}.json"
        assert prov_file.exists()

    def test_track_generation_with_empty_strings(self, temp_prov_dir):
        """Test tracking avec chaînes vides"""
        tracker = ProvenanceTracker(storage_dir=str(temp_prov_dir))

        prov_id = tracker.track_generation(
            conversation_id="conv-123", input_message="", output_message=""
        )

        prov_file = temp_prov_dir / f"prov_{prov_id}.json"
        assert prov_file.exists()

    def test_track_generation_with_special_characters(self, temp_prov_dir):
        """Test tracking avec caractères spéciaux"""
        tracker = ProvenanceTracker(storage_dir=str(temp_prov_dir))

        prov_id = tracker.track_generation(
            conversation_id="conv-éàü-123",
            input_message="Message avec accents: éàü",
            output_message="Réponse avec symboles: €£¥",
        )

        prov_file = temp_prov_dir / f"prov_{prov_id}.json"
        assert prov_file.exists()

        with open(prov_file, "r", encoding="utf-8") as f:
            prov_data = json.load(f)

        assert prov_data is not None


class TestW3CProvCompliance:
    """Test compliance with W3C PROV standard"""

    def test_prov_json_structure(self, prov_builder):
        """Test structure PROV-JSON conforme"""
        prov_builder.add_entity("entity:1", "Entity 1")
        prov_builder.add_activity("activity:1", "2025-01-01T00:00:00", "2025-01-01T00:01:00")
        prov_builder.add_agent("agent:1", "softwareAgent")

        prov_json = prov_builder.to_prov_json()

        # W3C PROV requires these top-level keys
        assert "entity" in prov_json
        assert "activity" in prov_json
        assert "agent" in prov_json

    def test_entity_has_prov_label(self, prov_builder):
        """Test que les entités ont prov:label"""
        prov_builder.add_entity("entity:1", "Test Entity")

        entity = prov_builder.entities["entity:1"]
        assert "prov:label" in entity

    def test_activity_has_required_fields(self, prov_builder):
        """Test que les activités ont les champs requis"""
        prov_builder.add_activity("activity:1", "2025-01-01T00:00:00", "2025-01-01T00:01:00")

        activity = prov_builder.activities["activity:1"]
        assert "prov:type" in activity
        assert "prov:startTime" in activity
        assert "prov:endTime" in activity

    def test_agent_has_prov_type(self, prov_builder):
        """Test que les agents ont prov:type"""
        prov_builder.add_agent("agent:1", "softwareAgent")

        agent = prov_builder.agents["agent:1"]
        assert "prov:type" in agent

    def test_relationships_have_required_fields(self, prov_builder):
        """Test que les relations ont les champs requis"""
        prov_builder.link_generated("entity:1", "activity:1")

        rel = prov_builder.was_generated_by[0]
        assert "prov:entity" in rel
        assert "prov:activity" in rel

    def test_prov_json_is_serializable(self, temp_prov_dir):
        """Test que PROV-JSON est sérialisable"""
        tracker = ProvenanceTracker(storage_dir=str(temp_prov_dir))

        prov_id = tracker.track_generation(
            conversation_id="conv-123", input_message="Test", output_message="Response"
        )

        prov_file = temp_prov_dir / f"prov_{prov_id}.json"

        # Should be able to load as JSON
        with open(prov_file, "r") as f:
            data = json.load(f)

        # Should be able to serialize back
        json.dumps(data)
