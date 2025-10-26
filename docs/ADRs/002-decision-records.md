# ADR 002 : Decision Records (DR)

**Date**: 2025-10-26  
**Statut**: Accepté  
**Contexte**: Besoin de traçabilité décisionnelle pour conformité légale

## Contexte

L'article 6.1 de la Loi 25 (Québec) et l'article 22 du RGPD exigent la transparence des décisions automatisées. Il faut pouvoir expliquer une décision automatisée.

## Décision

Implémenter des Decision Records (DR) selon les spécifications de FilAgent.md:
- Format JSON avec tous les champs requis
- Signatures EdDSA pour authenticité
- Génération automatique pour actions significatives
- Sauvegarde dans `logs/decisions/`

**Champs obligatoires** :
- dr_id, timestamp, actor, task_id
- decision, tools_used, constraints, expected_risk
- alternatives_considered, reasoning_markers
- Signature cryptographique

## Conséquences

**Positives** :
- Traçabilité complète des décisions
- Conformité légale
- Audit trail vérifiable cryptographiquement

**Alternatives considérées** :
- Logs simples → Rejetée (pas assez structuré)
- Base de données centralisée → Gardée pour futur avec provenenance
