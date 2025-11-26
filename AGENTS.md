# Repository Guidelines

## Project Structure & Modules
- `runtime/` hosts the FastAPI entrypoint, middleware, and agent orchestration; HTN planning and verification are in `planner/`; shared tools live in `tools/`; persistence and retention logic are in `memory/`; RBAC and guardrails live in `policy/`.
- Defaults and knobs sit in `config/` (agent, policies, retention, provenance). Optional local weights reside in `models/weights/`. Logs and metrics stream to `logs/` and dashboards in `grafana/`.
- Tests are under `tests/` with suite READMEs; shared fixtures/helpers are in `tests/utils/` and `fixtures/`.

## Build, Test, and Dev Commands
- Install: `pdm install --dev` (or `pip install -r requirements.txt` plus `requirements-dev.txt` if PDM is unavailable).
- Run locally: `pdm run server-dev` for hot reload (localhost:8000) or `pdm run server` for production-like start.
- Tests: `pdm run test` for the full suite; `pdm run test-unit`, `test-integration`, `test-compliance`, `test-e2e`, or `test-performance` for scoped runs. Coverage: `pdm run test-cov` (HTML in `htmlcov/`).
- Quality: `pdm run format` (Black), `pdm run lint` (Flake8), `pdm run typecheck` (mypy); use `pdm run check` before opening a PR.

## Coding Style & Naming
- Target Python 3.10–3.12; Black with 100-char lines and isort (Black profile). Favor type hints on public surfaces and pure functions for planner/tool logic.
- Conventions: `snake_case` for functions/variables, `PascalCase` for classes, `SCREAMING_SNAKE` for constants, `kebab-case` for scripts. Configuration keys stay `lower_snake_case`; policy names remain explicit (e.g., `compliance_guardian`, `worm_finalization`).

## Testing Guidelines
- Use `pytest` markers `unit`, `integration`, `compliance`, `e2e`, `performance`; keep fast, isolated tests in `unit`.
- Name files `test_*.py` mirroring runtime/planner/tool modules. Reuse fixtures in `tests/utils/` instead of custom setup. Avoid network calls in CI and prefer deterministic seeds for planner/tool behavior.
- Check `htmlcov/index.html` when changing middleware, policy, or retention paths to avoid silent coverage drops.

## Commit & Pull Request Guidelines
- Match the repo’s conventional style: `type: summary` (e.g., `feat: add retention overrides`, `fix: harden audit hashing`, `test: mark llama-cpp optional`); imperative, ~72-char subjects.
- PRs should include scope, linked issues/tasks, test evidence (`pdm run test` plus targeted suites), and screenshots or logs for API/metrics/UI changes. Call out privacy/compliance impacts and rollout notes.

## Security & Configuration Tips
- Never commit secrets; derive `.env` from `.env.example`. Update `config/policies.yaml` alongside code that touches RBAC/redaction. Keep provenance/retention changes backward-compatible.
- New tools must include RBAC/policy checks in `runtime/middleware/` and tests in `tests/test_tools*.py`; ensure audit/log paths stay WORM-friendly.
