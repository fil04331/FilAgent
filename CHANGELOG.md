# CHANGELOG

## [Unreleased]

### Added
- **Audit MLOps** (2026-02-06): Audit complet post-merge avec plan d'action 4 sprints
  - `AUDIT_POST_MERGE_MLOPS.md`: Rapport d'audit détaillé (15 pages)
  - `PLAN_ACTION_AMELIORATION.md`: Plan d'action sur 4 sprints (20 pages)
  - `EXECUTIVE_SUMMARY_AUDIT.md`: Résumé exécutif pour la direction
  - `QUICKSTART_SPRINT1.md`: Guide quick start pour développeurs
  - Identification de 10 défectuosités avec priorisation
  - Métriques actuelles: 95.5% tests passants, 84.46% couverture
  - Verdict: 🟢 BON (8.1/10) - Production-ready après corrections Sprint 1

### Changed
- **Documentation** (2025-12-16): Nettoyage et archivage de la documentation
  - Archivé 11 documents temporaires et rapports historiques vers `docs/archive/`
  - Documents archivés: rapports de tests (ANALYSE_TESTS_RESUME, COVERAGE_REPORT, TEST_DIAGNOSTIC_REPORT), implémentations complétées (OPENTELEMETRY_IMPLEMENTATION_SUMMARY, SEMANTIC_CACHE_IMPLEMENTATION, TEMPLATE_MIGRATION_SUMMARY), rapports de développement (IMPLEMENTATION_REPORT_DEC8, REFACTORING_SUMMARY), et documents de planification (PLAN-ACTION-DEC8, CI_CD_VERIFICATION_CHECKLIST, ARCHITECTURE_OVERVIEW)
  - Mise à jour de `docs/archive/README.md` avec références aux nouveaux documents archivés
  - La racine du dépôt contient maintenant 6 fichiers MD essentiels au lieu de 17
  - Amélioration de la découvrabilité et réduction de la surcharge cognitive pour les nouveaux contributeurs
  - Voir `docs/archive/README.md` pour accéder aux documents archivés

---

## [v2025.12.13-security-patch]

_Security Release_

This release addresses a security vulnerability related to PyPDF2.

- [SECURITY] Replaced PyPDF2 with pypdf=>3.9.0 (CVET2023-36464)
- [Tests] Validated and passed completely (pytest)
- [Security] No remaining volnerabilities (Safety + Pip-Audit)
- [CodeQL] Completed without critical issues

- Release created by GitHub Action Automation
- Merged into develop from Main
- Tagged: v2025.12.13-security-patch
