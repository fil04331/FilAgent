#!/usr/bin/env python3
"""Validation du spec OpenAPI (3.0.x).

- Cherche `openapi.yaml` à la racine, sinon `audit/CURSOR TODOS/openapi.yaml`.
- Valide via openapi-spec-validator.
- Retourne code 1 si la validation échoue.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Tuple

from openapi_spec_validator import validate_spec
from openapi_spec_validator.readers import read_from_filename


def _find_openapi_file(repo_root: Path) -> Path:
    primary = repo_root / "openapi.yaml"
    if primary.exists():
        return primary
    return repo_root / "audit" / "CURSOR TODOS" / "openapi.yaml"


def validate_openapi_spec() -> Tuple[bool, str]:
    repo_root = Path(__file__).parent.parent
    spec_path = _find_openapi_file(repo_root)

    if not spec_path.exists():
        return False, f"Fichier introuvable: {spec_path}"

    try:
        spec_dict, _ = read_from_filename(str(spec_path))
        validate_spec(spec_dict)
        return True, f"✅ OpenAPI spec valide: {spec_path}"
    except Exception as exc:
        return False, f"❌ Échec validation OpenAPI: {exc}"


if __name__ == "__main__":
    ok, message = validate_openapi_spec()
    print(message)
    sys.exit(0 if ok else 1)
