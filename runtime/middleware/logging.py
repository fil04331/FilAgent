"""Middleware de journalisation JSONL compatible OpenTelemetry et WORM."""

from __future__ import annotations

import json
import os
import traceback
from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Optional, Union
from pathlib import Path
import threading
import hashlib

from .worm import get_worm_logger

# Type aliases for strict typing
LogMetadataValue = Union[str, int, float, bool, None]
LogMetadataDict = Dict[str, Union[LogMetadataValue, List[LogMetadataValue], "LogMetadataDict"]]
EventPayload = Dict[str, Union[str, int, float, bool, None, LogMetadataDict]]


class EventLogger:
    """
    Logger pour evenements structures
    Format JSONL (une ligne = un evenement)
    Compatible OpenTelemetry
    """

    def __init__(self, log_dir: str = "logs/events") -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

        # Fichier du jour actuel
        self.current_file = self._get_today_log_file()
        try:
            self.worm_logger = get_worm_logger()
        except Exception as exc:
            print(f"Warning: Failed to initialize WORM logger: {exc}")
            self.worm_logger = None

    def _get_today_log_file(self) -> Path:
        """Obtenir le fichier de log du jour actuel"""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.log_dir / f"events-{today}.jsonl"

    def _write_line(self, line: str) -> None:
        """Ecrire une ligne dans le fichier de log (append-only)"""
        with self._lock:
            # Verifier si on doit changer de fichier (nouveau jour)
            today_file = self._get_today_log_file()
            if today_file != self.current_file:
                self.current_file = today_file

            # Essayer d'utiliser le logger WORM (append-only renforce)
            if getattr(self, "worm_logger", None):
                if self.worm_logger.append(line, log_file=self.current_file):
                    return

            # Fallback en ecriture standard si WORM indisponible
            with open(self.current_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()  # Force l'ecriture immediate
                os.fsync(f.fileno())

    def _apply_pii_redaction(self, metadata: LogMetadataDict) -> LogMetadataDict:
        """Appliquer le masquage PII sur les metadonnees si configure."""

        try:
            from .redaction import get_pii_redactor

            redactor = get_pii_redactor()
        except Exception as exc:
            print(f"Warning: Failed to initialize PII redactor: {exc}")
            return metadata

        def _redact(
            value: Union[str, int, float, bool, None, Dict[str, object], List[object]],
            path: str,
        ) -> Union[str, int, float, bool, None, Dict[str, object], List[object]]:
            if isinstance(value, str):
                try:
                    scan_result = redactor.scan_and_log(value, context={"field": path})
                    if scan_result.get("has_pii"):
                        return redactor.redact(value)
                except Exception as exc:
                    print(f"Warning: Failed to redact PII for {path}: {exc}")
                return value
            if isinstance(value, dict):
                return {key: _redact(val, f"{path}.{key}") for key, val in value.items()}
            if isinstance(value, list):
                return [_redact(item, f"{path}[{idx}]") for idx, item in enumerate(value)]
            return value

        result = _redact(metadata, "metadata")
        # Safe cast: _redact returns dict for dict input
        if isinstance(result, dict):
            return result  # type: ignore[return-value]
        return metadata

    def log_event(
        self,
        actor: str,
        event: str,
        level: str = "INFO",
        conversation_id: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[LogMetadataDict] = None,
    ) -> None:
        """
        Enregistrer un evenement

        Args:
            actor: Nom de l'acteur (ex: "agent.core", "tool.python_sandbox")
            event: Type d'evenement (ex: "tool.call", "generation.start")
            level: Niveau de log (DEBUG, INFO, WARNING, ERROR)
            conversation_id: ID de la conversation
            task_id: ID de la tache
            metadata: Metadonnees additionnelles
        """
        # Generer trace_id et span_id
        trace_id = self._generate_trace_id()
        span_id = self._generate_span_id()

        # Preparer les metadonnees (copie pour eviter les mutations externes)
        safe_metadata: LogMetadataDict = deepcopy(metadata) if metadata else {}

        # Appliquer le masquage PII (sauf pour les evenements du redactor)
        if actor != "pii.redactor" and safe_metadata:
            safe_metadata = self._apply_pii_redaction(safe_metadata)

        # Construire l'evenement
        event_data: EventPayload = {
            "ts": datetime.now().isoformat(),
            "timestamp": None,  # placeholder, will be set below
            "trace_id": trace_id,
            "span_id": span_id,
            "level": level,
            "actor": actor,
            "event": event,
            "conversation_id": conversation_id,
            "task_id": task_id,
            "metadata": safe_metadata,
        }

        # Alias pour compatibilite avec certains consommateurs
        event_data["timestamp"] = event_data["ts"]

        # Ajouter les references de hash si applicable
        if metadata and "input_ref" in metadata:
            event_data["input_ref"] = str(metadata["input_ref"])
        if metadata and "output_ref" in metadata:
            event_data["output_ref"] = str(metadata["output_ref"])

        # Serialiser en JSONL
        line = json.dumps(event_data, ensure_ascii=False)
        self._write_line(line)

    def _generate_trace_id(self) -> str:
        """Generer un trace_id unique"""
        timestamp = datetime.now().isoformat()
        random_str = os.urandom(8).hex()
        content = f"{timestamp}{random_str}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _generate_span_id(self) -> str:
        """Generer un span_id unique"""
        return os.urandom(8).hex()[:8]

    def log_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Union[str, int, float, bool, None]],
        conversation_id: str,
        task_id: Optional[str] = None,
        success: bool = True,
        output: Optional[str] = None,
    ) -> None:
        """Enregistrer un appel d'outil"""
        # Hasher les arguments sensibles
        input_hash = hashlib.sha256(str(arguments).encode()).hexdigest()
        output_hash: Optional[str] = None
        if output:
            output_hash = hashlib.sha256(str(output).encode()).hexdigest()

        metadata: LogMetadataDict = {
            "tool_name": tool_name,
            "arguments_hash": f"sha256:{input_hash}",
            "output_hash": f"sha256:{output_hash}" if output_hash else None,
            "success": success,
        }

        self.log_event(
            actor=f"tool.{tool_name}",
            event="tool.call",
            level="INFO",
            conversation_id=conversation_id,
            task_id=task_id,
            metadata=metadata,
        )

    def log_generation(
        self,
        conversation_id: str,
        task_id: Optional[str],
        prompt_hash: str,
        response_hash: str,
        tokens_used: int,
    ) -> None:
        """Enregistrer une generation de texte"""
        metadata: LogMetadataDict = {
            "prompt_hash": f"sha256:{prompt_hash}",
            "response_hash": f"sha256:{response_hash}",
            "tokens_used": tokens_used,
        }

        self.log_event(
            actor="agent.core",
            event="generation.complete",
            level="INFO",
            conversation_id=conversation_id,
            task_id=task_id,
            metadata=metadata,
        )

    def error(
        self,
        message: str,
        *,
        exc_info: Optional[Union[bool, BaseException]] = None,
        metadata: Optional[LogMetadataDict] = None,
    ) -> None:
        """Journaliser un message d'erreur structurel."""

        error_metadata: LogMetadataDict = deepcopy(metadata) if metadata else {}

        if exc_info:
            try:
                if exc_info is True:
                    stack = traceback.format_exc()
                elif isinstance(exc_info, BaseException):
                    stack = "".join(traceback.format_exception(exc_info))
                else:
                    stack = str(exc_info)
                error_metadata.setdefault("exception", stack)
            except Exception as exc:
                error_metadata.setdefault("exception", f"<failed to format exception: {exc}>")

        error_metadata.setdefault("message", message)
        self.log_event(
            actor="logger.system",
            event="error",
            level="ERROR",
            metadata=error_metadata,
        )


# Instance globale
_logger: Optional[EventLogger] = None


def get_logger() -> EventLogger:
    """Recuperer l'instance globale du logger"""
    global _logger
    if _logger is None:
        _logger = EventLogger()
    return _logger


def init_logger(log_dir: str = "logs/events") -> EventLogger:
    """Initialiser le logger"""
    global _logger
    _logger = EventLogger(log_dir)
    return _logger


def reset_logger() -> None:
    """Reset the global logger instance (primarily for testing)"""
    global _logger
    _logger = None
