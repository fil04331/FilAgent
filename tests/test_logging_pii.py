"""Tests de conformité du masquage PII dans les logs."""

import json
from pathlib import Path

from runtime.middleware.logging import get_logger, init_logger
from runtime.middleware.redaction import init_pii_redactor


def _write_minimal_policy(path: Path):
    path.write_text(
        """
policies:
  pii:
    enabled: true
    fields_to_mask:
      - "email"
      - "phone"
    replacement_pattern: "[REDACTED]"
    scan_before_logging: true
""".strip()
    )


def test_event_logger_masks_pii(tmp_path):
    policies_path = tmp_path / "policies.yaml"
    _write_minimal_policy(policies_path)

    init_pii_redactor(str(policies_path))

    log_dir = tmp_path / "logs"
    init_logger(str(log_dir))
    logger = get_logger()

    logger.log_event(
        actor="agent.core",
        event="unit_test",
        metadata={
            "email": "user@example.com",
            "note": "Contactez-moi au 514-555-1234",
        },
        conversation_id="conv-test",
    )

    log_files = sorted(log_dir.glob("events-*.jsonl"))
    assert log_files, "Aucun fichier de log généré"

    lines = [line for line in log_files[0].read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) >= 2, "Le scan PII devrait créer un log de détection + l'événement masqué"

    records = [json.loads(line) for line in lines]

    detection_event = next((record for record in records if record["actor"] == "pii.redactor"), None)
    assert detection_event is not None, "La détection PII devrait être consignée"
    assert detection_event["metadata"]["pii_count"] >= 1

    logged_event = next(
        (record for record in records if record["actor"] == "agent.core" and record["event"] == "unit_test"),
        None,
    )
    assert logged_event is not None, "L'événement initial doit être présent"
    assert logged_event["metadata"]["email"] == "[REDACTED]"
    assert "514-555-1234" not in logged_event["metadata"]["note"]
    assert "[REDACTED]" in logged_event["metadata"]["note"]

    # Réinitialiser les singletons globaux pour éviter les fuites entre tests
    from runtime.middleware import logging as logging_mw
    from runtime.middleware import redaction as redaction_mw

    logging_mw._logger = None
    redaction_mw._pii_redactor = None
