"""
Configuration management for FilAgent
Loads and validates configuration from YAML files
"""
import yaml
import os
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class GenerationConfig(BaseModel):
    """Configuration de génération du modèle"""
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    max_tokens: int = Field(default=800, ge=1, le=10000)
    seed: int = Field(default=42)
    top_k: int = Field(default=40, ge=1)
    repetition_penalty: float = Field(default=1.1, ge=0.0)


class TimeoutConfig(BaseModel):
    """Configuration des timeouts"""
    generation: int = Field(default=60)
    tool_execution: int = Field(default=30)
    total_request: int = Field(default=300)


class ModelConfig(BaseModel):
    """Configuration du modèle"""
    name: str = "llama-3"
    path: str = "models/weights/base.gguf"
    backend: str = "llama.cpp"
    context_size: int = 4096
    n_gpu_layers: int = 35


class MemoryConfig(BaseModel):
    """Configuration de la mémoire"""
    episodic_ttl_days: int = Field(default=30, alias="episodic.ttl_days")
    episodic_max_conversations: int = Field(default=1000, alias="episodic.max_conversations")
    semantic_rebuild_days: int = Field(default=14, alias="semantic.rebuild_days")
    semantic_max_items: int = Field(default=10000, alias="semantic.max_items")
    semantic_similarity_threshold: float = Field(default=0.7, alias="semantic.similarity_threshold")

    class Config:
        populate_by_name = True


class LoggingConfig(BaseModel):
    """Configuration du logging"""
    level: str = "INFO"
    rotate_daily: bool = True
    max_file_size_mb: int = 100
    compress_old: bool = True


class ComplianceConfig(BaseModel):
    """Configuration de conformité"""
    worm_enabled: bool = True
    dr_required_for: list[str] = Field(default=["write_file", "delete_file", "execute_code"])
    pii_redaction: bool = True
    provenance_tracking: bool = True


class AgentRuntimeSettings(BaseModel):
    """Configuration opérationnelle de l'agent"""
    max_iterations: int = 10
    timeout: int = 300


class HTNPlanningConfig(BaseModel):
    """Configuration de planification HTN"""
    enabled: bool = True
    default_strategy: str = "hybrid"  # rule_based, llm_based, hybrid
    max_decomposition_depth: int = 3


class HTNExecutionConfig(BaseModel):
    """Configuration d'exécution HTN"""
    default_strategy: str = "adaptive"  # sequential, parallel, adaptive
    max_parallel_workers: int = 4
    task_timeout_sec: int = 60


class HTNVerificationConfig(BaseModel):
    """Configuration de vérification HTN"""
    default_level: str = "strict"  # basic, strict, paranoid
    custom_verifiers: list[str] = Field(default_factory=list)


class AgentConfig(BaseModel):
    """Configuration principale de l'agent"""
    name: str = "llmagenta"
    version: str = "0.1.0"
    generation: GenerationConfig = GenerationConfig()
    timeouts: TimeoutConfig = TimeoutConfig()
    model: ModelConfig = ModelConfig()
    memory: MemoryConfig = MemoryConfig()
    logging: LoggingConfig = LoggingConfig()
    compliance: ComplianceConfig = ComplianceConfig()
    runtime_settings: AgentRuntimeSettings = AgentRuntimeSettings()
    htn_planning: Optional[HTNPlanningConfig] = None
    htn_execution: Optional[HTNExecutionConfig] = None
    htn_verification: Optional[HTNVerificationConfig] = None

    @classmethod
    def load(cls, config_dir: str = "config") -> "AgentConfig":
        """Charger la configuration depuis les fichiers YAML"""
        config_path = Path(config_dir) / "agent.yaml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            raw_config = yaml.safe_load(f)
        
        # Extraire et valider chaque section
        agent_data = raw_config.get('agent', {})
        generation_data = raw_config.get('generation', {})
        timeouts_data = raw_config.get('timeouts', {})
        model_data = raw_config.get('model', {})
        memory_data = raw_config.get('memory', {})
        logging_data = raw_config.get('logging', {})
        compliance_data = raw_config.get('compliance', {})
        htn_planning_data = raw_config.get('htn_planning', {})
        htn_execution_data = raw_config.get('htn_execution', {})
        htn_verification_data = raw_config.get('htn_verification', {})
        
        # Adapter la configuration mémoire pour supporter les structures imbriquées
        memory_kwargs: Dict[str, Any] = {}

        # Support des anciens formats à clés aplaties (aliases pydantic)
        for field_name, field in MemoryConfig.model_fields.items():
            alias = field.alias
            if field_name in memory_data:
                memory_kwargs[field_name] = memory_data[field_name]
            elif alias and alias in memory_data:
                memory_kwargs[field_name] = memory_data[alias]

        # Support du format YAML imbriqué actuel
        episodic_cfg = memory_data.get('episodic', {})
        if isinstance(episodic_cfg, dict):
            if 'ttl_days' in episodic_cfg:
                memory_kwargs.setdefault('episodic_ttl_days', episodic_cfg['ttl_days'])
            if 'max_conversations' in episodic_cfg:
                memory_kwargs.setdefault('episodic_max_conversations', episodic_cfg['max_conversations'])

        semantic_cfg = memory_data.get('semantic', {})
        if isinstance(semantic_cfg, dict):
            if 'rebuild_days' in semantic_cfg:
                memory_kwargs.setdefault('semantic_rebuild_days', semantic_cfg['rebuild_days'])
            if 'max_items' in semantic_cfg:
                memory_kwargs.setdefault('semantic_max_items', semantic_cfg['max_items'])
            if 'similarity_threshold' in semantic_cfg:
                memory_kwargs.setdefault('semantic_similarity_threshold', semantic_cfg['similarity_threshold'])

        memory_config = MemoryConfig(**memory_kwargs)

        runtime_settings = AgentRuntimeSettings()
        if 'max_iterations' in agent_data:
            runtime_settings.max_iterations = agent_data['max_iterations']
        if 'timeout' in agent_data:
            runtime_settings.timeout = agent_data['timeout']

        # Configurations HTN optionnelles
        htn_planning_config = HTNPlanningConfig(**htn_planning_data) if htn_planning_data else None
        htn_execution_config = HTNExecutionConfig(**htn_execution_data) if htn_execution_data else None
        htn_verification_config = HTNVerificationConfig(**htn_verification_data) if htn_verification_data else None
        
        return cls(
            name=agent_data.get('name', 'llmagenta'),
            version=agent_data.get('version', '0.1.0'),
            generation=GenerationConfig(**generation_data),
            timeouts=TimeoutConfig(**timeouts_data),
            model=ModelConfig(**model_data),
            memory=memory_config,
            logging=LoggingConfig(**logging_data),
            compliance=ComplianceConfig(**compliance_data),
            runtime_settings=runtime_settings,
            htn_planning=htn_planning_config,
            htn_execution=htn_execution_config,
            htn_verification=htn_verification_config,
        )

    @property
    def agent(self) -> AgentRuntimeSettings:
        """Compatibilité historique: expose les paramètres runtime via config.agent"""
        return self.runtime_settings

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary format suitable for YAML serialization.
        Dynamically builds the nested memory dictionary from MemoryConfig fields.
        """
        # Dynamically build the nested memory dictionary
        memory_dict = {"episodic": {}, "semantic": {}}
        for field_name in MemoryConfig.model_fields.keys():
            value = getattr(self.memory, field_name)
            if field_name.startswith("episodic_"):
                key = field_name.removeprefix("episodic_")
                memory_dict["episodic"][key] = value
            elif field_name.startswith("semantic_"):
                key = field_name.removeprefix("semantic_")
                memory_dict["semantic"][key] = value

        config_dict = {
            'agent': {
                'name': self.name,
                'version': self.version,
                'max_iterations': self.runtime_settings.max_iterations,
                'timeout': self.runtime_settings.timeout,
            },
            'generation': self.generation.model_dump(),
            'timeouts': self.timeouts.model_dump(),
            'model': self.model.model_dump(),
            'memory': memory_dict,
            'logging': self.logging.model_dump(),
            'compliance': self.compliance.model_dump(),
        }

        # Add optional HTN configurations if they exist
        if self.htn_planning is not None:
            config_dict['htn_planning'] = self.htn_planning.model_dump()
        if self.htn_execution is not None:
            config_dict['htn_execution'] = self.htn_execution.model_dump()
        if self.htn_verification is not None:
            config_dict['htn_verification'] = self.htn_verification.model_dump()

        return config_dict

    def save(self, config_path: str = "config/agent.yaml"):
        """Save the current configuration to a YAML file."""
        config_dict = self.to_dict()
        
        # Ensure directory exists
        path = Path(config_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save to YAML file
        with open(path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)


# Variable globale pour stocker la configuration
_config: AgentConfig | None = None


def get_config() -> AgentConfig:
    """Récupérer la configuration globale (singleton)"""
    global _config
    if _config is None:
        _config = AgentConfig.load()
    return _config


def reload_config() -> AgentConfig:
    """Recharger la configuration depuis les fichiers"""
    global _config
    _config = AgentConfig.load()
    return _config
