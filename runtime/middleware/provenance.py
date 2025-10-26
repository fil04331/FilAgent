"""
Middleware de provenance PROV-JSON
Traçabilité des artefacts selon le standard W3C PROV
"""
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import uuid


class ProvBuilder:
    """
    Builder pour construire des graphes de provenance PROV-JSON
    Format conforme W3C PROV
    """
    
    def __init__(self):
        self.entities: Dict[str, Dict] = {}
        self.activities: Dict[str, Dict] = {}
        self.agents: Dict[str, Dict] = {}
        self.was_generated_by: List[Dict] = []
        self.was_attributed_to: List[Dict] = []
        self.used: List[Dict] = []
        self.was_associated_with: List[Dict] = []
        self.was_derived_from: List[Dict] = []
    
    def add_entity(self, entity_id: str, label: str, attributes: Optional[Dict] = None):
        """
        Ajouter une entité (artifact)
        
        Args:
            entity_id: ID unique de l'entité
            label: Label descriptif
            attributes: Attributs additionnels (hash, type, etc.)
        """
        entity = {
            "prov:label": label
        }
        
        if attributes:
            entity.update(attributes)
        
        self.entities[entity_id] = entity
    
    def add_activity(self, activity_id: str, start_time: str, end_time: str):
        """
        Ajouter une activité (processus)
        
        Args:
            activity_id: ID unique de l'activité
            start_time: Timestamp de début (ISO8601)
            end_time: Timestamp de fin (ISO8601)
        """
        self.activities[activity_id] = {
            "prov:type": "Activity",
            "prov:startTime": start_time,
            "prov:endTime": end_time
        }
    
    def add_agent(self, agent_id: str, agent_type: str = "softwareAgent", 
                  version: Optional[str] = None):
        """
        Ajouter un agent
        
        Args:
            agent_id: ID de l'agent
            agent_type: Type (softwareAgent, person, organization)
            version: Version de l'agent
        """
        agent = {
            "prov:type": agent_type
        }
        
        if version:
            agent["version"] = version
        
        self.agents[agent_id] = agent
    
    def link_generated(self, entity_id: str, activity_id: str):
        """Lier une entité à l'activité qui l'a générée"""
        self.was_generated_by.append({
            "prov:entity": entity_id,
            "prov:activity": activity_id
        })
    
    def link_associated(self, activity_id: str, agent_id: str):
        """Lier une activité à l'agent qui l'a exécutée"""
        self.was_associated_with.append({
            "prov:activity": activity_id,
            "prov:agent": agent_id
        })
    
    def link_attributed(self, entity_id: str, agent_id: str):
        """Lier une entité à l'agent qui en est responsable"""
        self.was_attributed_to.append({
            "prov:entity": entity_id,
            "prov:agent": agent_id
        })
    
    def link_used(self, activity_id: str, entity_id: str):
        """Lier une activité à l'entité qu'elle a utilisée"""
        self.used.append({
            "prov:activity": activity_id,
            "prov:entity": entity_id
        })
    
    def link_derived(self, entity_id: str, source_entity_id: str):
        """Lier une entité dérivée à sa source"""
        self.was_derived_from.append({
            "prov:generatedEntity": entity_id,
            "prov:usedEntity": source_entity_id
        })
    
    def to_prov_json(self) -> Dict[str, Any]:
        """Convertir en format PROV-JSON"""
        prov = {
            "entity": self.entities,
            "activity": self.activities,
            "agent": self.agents
        }
        
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
    Enregistre la traçabilité complète des décisions
    """
    
    def __init__(self, output_dir: str = "logs/traces/otlp"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def track_generation(
        self,
        agent_id: str,
        agent_version: str,
        task_id: str,
        prompt_hash: str,
        response_hash: str,
        start_time: str,
        end_time: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Tracer une génération de texte
        
        Args:
            agent_id: ID de l'agent
            agent_version: Version de l'agent
            task_id: ID de la tâche
            prompt_hash: Hash SHA256 du prompt
            response_hash: Hash SHA256 de la réponse
            start_time: Timestamp de début (ISO8601)
            end_time: Timestamp de fin (ISO8601)
            metadata: Métadonnées additionnelles
        
        Returns:
            Dict PROV-JSON
        """
        builder = ProvBuilder()
        
        # IDs uniques
        response_entity_id = f"response:{task_id}"
        prompt_entity_id = f"prompt:{task_id}"
        activity_id = f"gen:{task_id}"
        
        # Entités
        builder.add_entity(
            response_entity_id,
            "Response JSON",
            {"hash": f"sha256:{response_hash}"}
        )
        builder.add_entity(
            prompt_entity_id,
            "Prompt",
            {"hash": f"sha256:{prompt_hash}"}
        )
        
        # Activité
        builder.add_activity(activity_id, start_time, end_time)
        if metadata:
            builder.activities[activity_id]["metadata"] = metadata
        
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
        filename = f"prov-{task_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(prov_json, f, indent=2)
        
        return prov_json
    
    def track_tool_execution(
        self,
        tool_name: str,
        tool_input_hash: str,
        tool_output_hash: str,
        task_id: str,
        start_time: str,
        end_time: str
    ) -> Dict[str, Any]:
        """
        Tracer l'exécution d'un outil
        
        Returns:
            Dict PROV-JSON
        """
        builder = ProvBuilder()
        
        # IDs
        input_id = f"tool_input:{task_id}:{tool_name}"
        output_id = f"tool_output:{task_id}:{tool_name}"
        activity_id = f"tool_exec:{task_id}:{tool_name}"
        
        # Entités
        builder.add_entity(input_id, f"Tool input: {tool_name}", 
                         {"hash": f"sha256:{tool_input_hash}"})
        builder.add_entity(output_id, f"Tool output: {tool_name}",
                          {"hash": f"sha256:{tool_output_hash}"})
        
        # Activité
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
        
        with open(filepath, 'w') as f:
            json.dump(prov_json, f, indent=2)
        
        return prov_json


# Instance globale
_tracker: Optional[ProvenanceTracker] = None


def get_tracker() -> ProvenanceTracker:
    """Récupérer l'instance globale du tracker"""
    global _tracker
    if _tracker is None:
        _tracker = ProvenanceTracker()
    return _tracker


def init_tracker(output_dir: str = "logs/traces/otlp") -> ProvenanceTracker:
    """Initialiser le tracker"""
    global _tracker
    _tracker = ProvenanceTracker(output_dir)
    return _tracker
