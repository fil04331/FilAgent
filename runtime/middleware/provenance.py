"""
Middleware de provenance PROV-JSON
Tracabilite des artefacts selon le standard W3C PROV
"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Union
from pathlib import Path


# Type aliases for strict typing
ProvAttributeValue = Union[str, int, float, bool, None]
ProvAttributes = Dict[str, ProvAttributeValue]
ProvEntity = Dict[str, Union[str, ProvAttributes]]
ProvActivity = Dict[str, Union[str, ProvAttributes]]
ProvAgent = Dict[str, Union[str, ProvAttributes]]
ProvRelation = Dict[str, str]
ProvJsonDocument = Dict[str, Union[Dict[str, ProvEntity], Dict[str, ProvActivity], Dict[str, ProvAgent], List[ProvRelation]]]
ToolCallDict = Dict[str, Union[str, int, float, bool, None, List[str], Dict[str, str]]]
MetadataDict = Dict[str, Union[str, int, float, bool, None]]


class ProvBuilder:
    """
    Builder pour construire des graphes de provenance PROV-JSON
    Format conforme W3C PROV
    """

    def __init__(self) -> None:
        self.entities: Dict[str, ProvEntity] = {}
        self.activities: Dict[str, ProvActivity] = {}
        self.agents: Dict[str, ProvAgent] = {}
        self.was_generated_by: List[ProvRelation] = []
        self.was_attributed_to: List[ProvRelation] = []
        self.used: List[ProvRelation] = []
        self.was_associated_with: List[ProvRelation] = []
        self.was_derived_from: List[ProvRelation] = []

    def add_entity(self, entity_id: str, label: str, attributes: Optional[ProvAttributes] = None) -> None:
        """
        Ajouter une entite (artifact)

        Args:
            entity_id: ID unique de l'entite
            label: Label descriptif
            attributes: Attributs additionnels (hash, type, etc.)
        """
        entity: ProvEntity = {"prov:label": label}

        if attributes:
            entity.update(attributes)

        self.entities[entity_id] = entity

    def add_activity(self, activity_id: str, start_time: str, end_time: str) -> None:
        """
        Ajouter une activite (processus)

        Args:
            activity_id: ID unique de l'activite
            start_time: Timestamp de debut (ISO8601)
            end_time: Timestamp de fin (ISO8601)
        """
        self.activities[activity_id] = {"prov:type": "Activity", "prov:startTime": start_time, "prov:endTime": end_time}

    def add_agent(self, agent_id: str, agent_type: str = "softwareAgent", version: Optional[str] = None) -> None:
        """
        Ajouter un agent

        Args:
            agent_id: ID de l'agent
            agent_type: Type (softwareAgent, person, organization)
            version: Version de l'agent
        """
        agent: ProvAgent = {"prov:type": agent_type}

        if version:
            agent["version"] = version

        self.agents[agent_id] = agent

    def link_generated(self, entity_id: str, activity_id: str) -> None:
        """Lier une entite a l'activite qui l'a generee"""
        self.was_generated_by.append({"prov:entity": entity_id, "prov:activity": activity_id})

    def link_associated(self, activity_id: str, agent_id: str) -> None:
        """Lier une activite a l'agent qui l'a executee"""
        self.was_associated_with.append({"prov:activity": activity_id, "prov:agent": agent_id})

    def link_attributed(self, entity_id: str, agent_id: str) -> None:
        """Lier une entite a l'agent qui en est responsable"""
        self.was_attributed_to.append({"prov:entity": entity_id, "prov:agent": agent_id})

    def link_used(self, activity_id: str, entity_id: str) -> None:
        """Lier une activite a l'entite qu'elle a utilisee"""
        self.used.append({"prov:activity": activity_id, "prov:entity": entity_id})

    def link_derived(self, entity_id: str, source_entity_id: str) -> None:
        """Lier une entite derivee a sa source"""
        self.was_derived_from.append({"prov:generatedEntity": entity_id, "prov:usedEntity": source_entity_id})

    def to_prov_json(self) -> ProvJsonDocument:
        """Convertir en format PROV-JSON"""
        prov: ProvJsonDocument = {"entity": self.entities, "activity": self.activities, "agent": self.agents}

        if self.was_generated_by:
            prov["wasGeneratedBy"] = self.was_generated_by
        if self.was_attributed_to:
            prov["wasAttributedTo"] = self.was_attributed_to
        if self.used:
            prov["used"] = self.used
        if self.was_associated_with:
            prov["wasAssociatedWith"] = self.was_associated_with
        if self.was_derived_from:
            prov["wasDerivedFrom"] = self.was_derived_from

        return prov


class ProvenanceTracker:
    """
    Tracker de provenance pour l'agent
    Enregistre la tracabilite complete des decisions
    """

    def __init__(self, storage_dir: str = "logs/traces/otlp") -> None:
        self.output_dir = Path(storage_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def track_generation(
        self,
        conversation_id: Optional[str] = None,
        input_message: Optional[str] = None,
        output_message: Optional[str] = None,
        tool_calls: Optional[List[ToolCallDict]] = None,
        metadata: Optional[MetadataDict] = None,
        # Legacy parameters for backward compatibility
        agent_id: Optional[str] = None,
        agent_version: Optional[str] = None,
        task_id: Optional[str] = None,
        prompt_hash: Optional[str] = None,
        response_hash: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> str:
        """
        Tracer une generation de texte

        Supports two calling conventions:
        1. New API: conversation_id, input_message, output_message, tool_calls, metadata
        2. Legacy API: agent_id, agent_version, task_id, prompt_hash, response_hash, start_time, end_time, metadata

        Returns:
            Provenance ID (str)
        """
        import uuid

        # Determine which API is being used
        if conversation_id is not None:
            # New API
            prov_id = f"prov-{conversation_id}-{uuid.uuid4().hex[:8]}"

            # Calculate hashes
            if input_message:
                prompt_hash = hashlib.sha256(input_message.encode()).hexdigest()
            else:
                prompt_hash = "empty"

            if output_message:
                response_hash = hashlib.sha256(output_message.encode()).hexdigest()
            else:
                response_hash = "empty"

            # Generate timestamps
            now = datetime.now().isoformat()
            start_time = now
            end_time = now

            # Use conversation_id as task_id
            task_id = conversation_id
            agent_id = "filagent"
            agent_version = "1.0.0"
        else:
            # Legacy API
            prov_id = f"prov-{task_id}-{uuid.uuid4().hex[:8]}"
            # Ensure prompt_hash and response_hash have default values
            if prompt_hash is None:
                prompt_hash = "empty"
            if response_hash is None:
                response_hash = "empty"
            if start_time is None:
                start_time = datetime.now().isoformat()
            if end_time is None:
                end_time = datetime.now().isoformat()
            if agent_id is None:
                agent_id = "filagent"
            if agent_version is None:
                agent_version = "1.0.0"
            if task_id is None:
                task_id = "unknown"

        builder = ProvBuilder()

        # IDs uniques
        response_entity_id = f"response:{task_id}"
        prompt_entity_id = f"prompt:{task_id}"
        activity_id = f"gen:{task_id}"

        # Entites
        builder.add_entity(response_entity_id, "Response JSON", {"hash": f"sha256:{response_hash}"})
        builder.add_entity(prompt_entity_id, "Prompt", {"hash": f"sha256:{prompt_hash}"})

        # Activite
        builder.add_activity(activity_id, start_time, end_time)
        if metadata:
            # Store metadata in the activity dict
            activity_dict = self.activities[activity_id] if hasattr(self, 'activities') else builder.activities[activity_id]
            activity_dict["metadata"] = metadata  # type: ignore[assignment]

        # Agent
        builder.add_agent(agent_id, "softwareAgent", agent_version)

        # Liens
        builder.link_generated(response_entity_id, activity_id)
        builder.link_associated(activity_id, agent_id)
        builder.link_used(activity_id, prompt_entity_id)
        builder.link_derived(response_entity_id, prompt_entity_id)

        # Convertir en PROV-JSON
        prov_json = builder.to_prov_json()

        # Sauvegarder
        filename = f"prov_{prov_id}.json"
        filepath = self.output_dir / filename

        with open(filepath, "w") as f:
            json.dump(prov_json, f, indent=2)

        return prov_id

    def track_tool_execution(
        self, tool_name: str, tool_input_hash: str, tool_output_hash: str, task_id: str, start_time: str, end_time: str
    ) -> ProvJsonDocument:
        """
        Tracer l'execution d'un outil

        Returns:
            Dict PROV-JSON
        """
        builder = ProvBuilder()

        # IDs
        input_id = f"tool_input:{task_id}:{tool_name}"
        output_id = f"tool_output:{task_id}:{tool_name}"
        activity_id = f"tool_exec:{task_id}:{tool_name}"

        # Entites
        builder.add_entity(input_id, f"Tool input: {tool_name}", {"hash": f"sha256:{tool_input_hash}"})
        builder.add_entity(output_id, f"Tool output: {tool_name}", {"hash": f"sha256:{tool_output_hash}"})

        # Activite
        builder.add_activity(activity_id, start_time, end_time)

        # Agent (l'outil)
        builder.add_agent(f"tool:{tool_name}", "softwareAgent")
        builder.link_associated(activity_id, f"tool:{tool_name}")

        # Liens
        builder.link_generated(output_id, activity_id)
        builder.link_used(activity_id, input_id)
        builder.link_derived(output_id, input_id)

        prov_json = builder.to_prov_json()

        # Sauvegarder
        filename = f"prov-tool-{tool_name}-{task_id}.json"
        filepath = self.output_dir / filename

        with open(filepath, "w") as f:
            json.dump(prov_json, f, indent=2)

        return prov_json


# Instance globale
_tracker: Optional[ProvenanceTracker] = None


def get_tracker() -> ProvenanceTracker:
    """Recuperer l'instance globale du tracker"""
    global _tracker
    if _tracker is None:
        _tracker = ProvenanceTracker()
    return _tracker


def init_tracker(storage_dir: str = "logs/traces/otlp") -> ProvenanceTracker:
    """Initialiser le tracker"""
    global _tracker
    _tracker = ProvenanceTracker(storage_dir)
    return _tracker
