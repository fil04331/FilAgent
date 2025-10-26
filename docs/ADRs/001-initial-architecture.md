# ADR 001 : Architecture Initiale - Système de Conformité et Traçabilité

**Date**: 2025-10-26  
**Statut**: Accepté  
**Contexte**: Décision d'architecture initiale pour FilAgent

## Contexte

Le projet FilAgent nécessite un système d'agent LLM avec:
- Traçabilité légale complète
- Conformité Loi 25 (Québec), RGPD, AI Act
- Capacités agentiques (outils, raisonnement)
- Mémoire épisodique et sémantique
- Policy engine (RBAC, PII, guardrails)

## Décision

Architecture modulaire avec séparation des préoccupations:

1. **Mémoire** : SQLite épisodique + FAISS sémantique
2. **Conformité** : Middlewares séparés (logging, WORM, DR, provenance)
3. **Policy** : Engine indépendant (RBAC, PII, guardrails)
4. **Runtime** : API FastAPI, agent core, modèle abstrait
5. **Tools** : Sandbox isolé avec registre central

## Conséquences

**Positives** :
- Modularité et extensibilité
- Conformité dès la conception
- Tests isolés par module

**Négatives** :
- Complexité accrue
- Mais justifiée par les besoins légaux

**Alternatives considérées** :
- Architecture monolithique → Rejetée (pas de séparation des préoccupations)
- Architecture microservices → Rejetée (overkill pour MVP)
