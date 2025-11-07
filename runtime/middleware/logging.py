"""Middleware de journalisation JSONL compatible OpenTelemetry et WORM."""

import json
import os
from copy import deepcopy
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import threading
import hashlib

from .worm import get_worm_logger


class EventLogger:
    """
    Logger pour événements structurés
    Format JSONL (une ligne = un événement)
    Compatible OpenTelemetry
    """
    
    def __init__(self, log_dir: str = "logs/events"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

        # Fichier du jour actuel
        self.current_file = self._get_today_log_file()
        try:
            self.worm_logger = get_worm_logger()
        except Exception as exc:
            print(f"⚠ Failed to initialize WORM logger: {exc}")
            self.worm_logger = None

    def _redact_event_data(self, event_data: Dict[str, Any], actor: str, event_name: str) -> Dict[str, Any]:
        """Masquer toute PII avant écriture."""
        if actor == "pii.redactor":
            return event_data

        try:
            from runtime.middleware.redaction import get_pii_redactor
        except Exception as exc:
            print(f"⚠ Failed to load PII redactor: {exc}")
            return event_data

        redactor = get_pii_redactor()
        if not getattr(redactor, "enabled", False):
            return event_data

        detector = getattr(redactor, "detector", None)
        if detector is None:
            return event_data

        should_log_detection = getattr(redactor, "scan_before_logging", True)
        sanitized = deepcopy(event_data)

        def sanitize(value: Any, path: str) -> Any:
            if isinstance(value, str):
                if not value:
                    return value

                detected = detector.detect(value)
                if detected:
                    if should_log_detection:
                        redactor.scan_and_log(
                            value,
                            context={
                                "actor": actor,
                                "event": event_name,
                                "field": path or "root",
                            },
                        )
                    return detector.redact(value, redactor.replacement_pattern)
                return value

            if isinstance(value, dict):
                return {
                    key: sanitize(val, f"{path}.{key}" if path else key)
                    for key, val in value.items()
                }

            if isinstance(value, list):
                return [
                    sanitize(item, f"{path}[{idx}]" if path else f"[{idx}]")
                    for idx, item in enumerate(value)
                ]

            return value

        return sanitize(sanitized, "")
    
    def _get_today_log_file(self) -> Path:
        """Obtenir le fichier de log du jour actuel"""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.log_dir / f"events-{today}.jsonl"
    
    def _write_line(self, line: str):
        """Écrire une ligne dans le fichier de log (append-only)"""
        with self._lock:
            # Vérifier si on doit changer de fichier (nouveau jour)
            today_file = self._get_today_log_file()
            if today_file != self.current_file:
                self.current_file = today_file

            # Essayer d'utiliser le logger WORM (append-only renforcé)
            if getattr(self, "worm_logger", None):
                if self.worm_logger.append(line, log_file=self.current_file):
                    return

            # Fallback en écriture standard si WORM indisponible
            with open(self.current_file, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
                f.flush()  # Force l'écriture immédiate
                os.fsync(f.fileno())
    
    def log_event(
        self,
        actor: str,
        event: str,
        level: str = "INFO",
        conversation_id: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Enregistrer un événement
        
        Args:
            actor: Nom de l'acteur (ex: "agent.core", "tool.python_sandbox")
            event: Type d'événement (ex: "tool.call", "generation.start")
            level: Niveau de log (DEBUG, INFO, WARNING, ERROR)
            conversation_id: ID de la conversation
            task_id: ID de la tâche
            metadata: Métadonnées additionnelles
        """
        # Générer trace_id et span_id
        trace_id = self._generate_trace_id()
        span_id = self._generate_span_id()
        
        # Construire l'événement
        event_data = {
            "ts": datetime.now().isoformat(),
            "timestamp": None,  # placeholder, will be set below
            "trace_id": trace_id,
            "span_id": span_id,
            "level": level,
            "actor": actor,
            "event": event,
            "conversation_id": conversation_id,
            "task_id": task_id,
            "metadata": metadata or {}
        }

        # Alias pour compatibilité avec certains consommateurs
        event_data["timestamp"] = event_data["ts"]

        # Ajouter les références de hash si applicable
        if "input_ref" in (metadata or {}):
            event_data["input_ref"] = metadata["input_ref"]
        if "output_ref" in (metadata or {}):
            event_data["output_ref"] = metadata["output_ref"]

        event_data = self._redact_event_data(event_data, actor, event)

        # Sérialiser en JSONL
        line = json.dumps(event_data, ensure_ascii=False)
        self._write_line(line)
    
    def _generate_trace_id(self) -> str:
        """Générer un trace_id unique"""
        timestamp = datetime.now().isoformat()
        random_str = os.urandom(8).hex()
        content = f"{timestamp}{random_str}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _generate_span_id(self) -> str:
        """Générer un span_id unique"""
        return os.urandom(8).hex()[:8]
    
    def log_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        conversation_id: str,
        task_id: Optional[str] = None,
        success: bool = True,
        output: Optional[str] = None
    ):
        """Enregistrer un appel d'outil"""
        # Hasher les arguments sensibles
        input_hash = hashlib.sha256(str(arguments).encode()).hexdigest()
        output_hash = None
        if output:
            output_hash = hashlib.sha256(str(output).encode()).hexdigest()
        
        metadata = {
            "tool_name": tool_name,
            "arguments_hash": f"sha256:{input_hash}",
            "output_hash": f"sha256:{output_hash}" if output_hash else None,
            "success": success
        }
        
        self.log_event(
            actor=f"tool.{tool_name}",
            event="tool.call",
            level="INFO",
            conversation_id=conversation_id,
            task_id=task_id,
            metadata=metadata
        )
    
    def log_generation(
        self,
        conversation_id: str,
        task_id: Optional[str],
        prompt_hash: str,
        response_hash: str,
        tokens_used: int
    ):
        """Enregistrer une génération de texte"""
        metadata = {
            "prompt_hash": f"sha256:{prompt_hash}",
            "response_hash": f"sha256:{response_hash}",
            "tokens_used": tokens_used
        }
        
        self.log_event(
            actor="agent.core",
            event="generation.complete",
            level="INFO",
            conversation_id=conversation_id,
            task_id=task_id,
            metadata=metadata
        )


# Instance globale
_logger: Optional[EventLogger] = None


def get_logger() -> EventLogger:
    """Récupérer l'instance globale du logger"""
    global _logger
    if _logger is None:
        _logger = EventLogger()
    return _logger


def init_logger(log_dir: str = "logs/events"):
    """Initialiser le logger"""
    global _logger
    _logger = EventLogger(log_dir)
    return _logger
