"""
Configuration management for FilAgent
Loads and validates configuration from YAML files
"""
import yaml
import os
from pathlib import Path
from typing import Any, Dict
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
        
        return cls(
            name=agent_data.get('name', 'llmagenta'),
            version=agent_data.get('version', '0.1.0'),
            generation=GenerationConfig(**generation_data),
            timeouts=TimeoutConfig(**timeouts_data),
            model=ModelConfig(**model_data),
            memory=MemoryConfig(**memory_data),
            logging=LoggingConfig(**logging_data),
            compliance=ComplianceConfig(**compliance_data),
        )

    def save(self, config_path: str = "config/agent.yaml"):
        """Sauvegarder la configuration actuelle"""
        # TODO: Implémenter la sauvegarde si nécessaire
        pass


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
