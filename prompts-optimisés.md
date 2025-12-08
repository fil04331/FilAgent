# Prompts Optimisés

## Introduction

Ce document présente une collection de prompts optimisés pour différentes phases du développement logiciel. Ces prompts sont conçus pour maximiser l'efficacité et la précision des interactions avec les modèles de langage (LLM) dans le contexte du projet FilAgent.

### Objectifs
- Standardiser les interactions avec les LLMs
- Améliorer la qualité et la cohérence des réponses
- Faciliter la traçabilité et la gouvernance des LLMs
- Optimiser les résultats pour chaque phase du développement

---

## Prompts de Base

Cette section contient les prompts fondamentaux utilisés pour les tâches courantes.

### Analyse de Code
```
Analyse le code suivant et identifie:
- Les vulnérabilités potentielles
- Les opportunités d'optimisation
- Les bonnes pratiques non respectées
- Les améliorations suggérées

[INSÉRER LE CODE ICI]
```

### Documentation de Fonction
```
Génère une documentation complète pour cette fonction, incluant:
- Description fonctionnelle
- Paramètres (types, descriptions, valeurs par défaut)
- Valeur de retour
- Exemples d'utilisation
- Cas limites et erreurs possibles

[INSÉRER LA FONCTION ICI]
```

### Révision de Code
```
Effectue une révision de code approfondie en évaluant:
- La lisibilité et la maintenabilité
- La conformité aux standards du projet
- La performance et l'efficacité
- La gestion des erreurs
- Les tests de couverture

[INSÉRER LE CODE À RÉVISER]
```

---

## Prompts Avancés

Cette section contient des prompts pour des tâches complexes et spécialisées.

### Architecture et Design Patterns
```
Propose une architecture logicielle pour le système suivant:
- Contexte: [DÉCRIRE LE CONTEXTE]
- Exigences fonctionnelles: [LISTER LES EXIGENCES]
- Contraintes techniques: [LISTER LES CONTRAINTES]
- Patterns recommandés et justification
- Diagrammes d'architecture (description textuelle)
- Stratégies de scalabilité et de résilience
```

### Optimisation de Performance
```
Analyse les goulots d'étranglement de performance dans ce code:
1. Identifie les sections critiques
2. Mesure la complexité algorithmique
3. Propose des optimisations concrètes
4. Estime l'impact des améliorations
5. Suggère des outils de profilage adaptés

[INSÉRER LE CODE À OPTIMISER]
```

### Refactoring Stratégique
```
Plan de refactoring pour améliorer ce code:
- État actuel: analyse des problèmes
- Objectifs du refactoring
- Étapes de transformation (avec priorités)
- Stratégie de migration progressive
- Tests de non-régression recommandés
- Métriques de succès

[INSÉRER LE CODE À REFACTORISER]
```

### Migration et Modernisation
```
Stratégie de migration de [TECHNOLOGIE SOURCE] vers [TECHNOLOGIE CIBLE]:
- Analyse de compatibilité
- Mapping des fonctionnalités
- Plan de migration par phases
- Risques et mitigation
- Stratégie de rollback
- Formation et documentation nécessaires

[INSÉRER LE CONTEXTE DU PROJET]
```

---

## Prompts de Test

Cette section est dédiée aux prompts pour la génération et l'optimisation de tests.

### Génération de Tests Unitaires
```
Génère une suite complète de tests unitaires pour cette fonction:
- Tests de cas nominaux
- Tests de cas limites (edge cases)
- Tests de gestion d'erreurs
- Tests de validation des entrées
- Mocks et fixtures nécessaires
- Coverage attendu: > 90%

Framework de test: [SPÉCIFIER LE FRAMEWORK]

[INSÉRER LA FONCTION À TESTER]
```

### Tests d'Intégration
```
Conçois des tests d'intégration pour ce module:
- Scénarios d'interaction entre composants
- Configuration de l'environnement de test
- Données de test réalistes
- Assertions sur les comportements attendus
- Gestion des dépendances externes

[INSÉRER LA DESCRIPTION DU MODULE]
```

### Tests de Performance
```
Crée des tests de performance pour évaluer:
- Temps de réponse sous charge normale
- Comportement sous charge élevée
- Limites de scalabilité
- Consommation de ressources (CPU, mémoire)
- Stratégies de stress testing

[INSÉRER LE COMPOSANT À TESTER]
```

### Stratégie de Test End-to-End
```
Élabore une stratégie de tests E2E incluant:
- Parcours utilisateur critiques
- Environnements de test
- Outils d'automatisation recommandés
- Critères de succès et métriques
- Maintenance des tests

[INSÉRER LA DESCRIPTION DE L'APPLICATION]
```

---

## Prompts de Déploiement

Cette section couvre les prompts pour les phases de déploiement et d'opérations.

### Configuration CI/CD
```
Génère une configuration CI/CD complète pour:
- Plateforme: [GitHub Actions / GitLab CI / Jenkins / etc.]
- Étapes: build, test, lint, security scan, deploy
- Environnements: dev, staging, production
- Stratégies de rollback
- Notifications et alertes
- Gestion des secrets

[INSÉRER LES SPÉCIFICATIONS DU PROJET]
```

### Infrastructure as Code
```
Crée une configuration IaC pour déployer:
- Infrastructure: [AWS / Azure / GCP / etc.]
- Composants: [LISTER LES COMPOSANTS]
- Outil: [Terraform / CloudFormation / Pulumi / etc.]
- Bonnes pratiques de sécurité
- Gestion des états et versioning
- Documentation des ressources

[INSÉRER LES EXIGENCES D'INFRASTRUCTURE]
```

### Stratégie de Déploiement
```
Définis une stratégie de déploiement pour:
- Type: [Blue-Green / Canary / Rolling / etc.]
- Validation pre-déploiement
- Monitoring post-déploiement
- Critères de succès/échec
- Procédures de rollback
- Communication aux stakeholders

[INSÉRER LE CONTEXTE DU DÉPLOIEMENT]
```

### Monitoring et Observabilité
```
Mets en place une stratégie de monitoring:
- Métriques clés à surveiller
- Logs et tracing distribué
- Alertes et seuils critiques
- Dashboards recommandés
- Outils: [Prometheus, Grafana, ELK, etc.]
- Plan de réponse aux incidents

[INSÉRER L'ARCHITECTURE DU SYSTÈME]
```

### Documentation de Déploiement
```
Rédige une documentation de déploiement complète:
- Prérequis et dépendances
- Procédures pas à pas
- Configuration des environnements
- Troubleshooting commun
- Contacts et escalade
- Checklist de validation

[INSÉRER LES DÉTAILS DU SYSTÈME]
```

---

## Notes et Bonnes Pratiques

### Conseils d'Utilisation
1. **Contextualiser**: Toujours fournir un contexte suffisant au LLM
2. **Itérer**: Affiner les prompts en fonction des résultats obtenus
3. **Traçabilité**: Documenter les prompts utilisés et les réponses obtenues
4. **Validation**: Toujours vérifier et valider les réponses du LLM
5. **Sécurité**: Ne jamais inclure de données sensibles dans les prompts

### Évolution du Document
Ce document est vivant et doit être mis à jour régulièrement:
- Ajouter de nouveaux prompts selon les besoins
- Affiner les prompts existants basés sur les retours d'expérience
- Partager les meilleures pratiques découvertes
- Supprimer ou archiver les prompts obsolètes

### Contribution
Pour ajouter de nouveaux prompts:
1. Identifier la catégorie appropriée
2. Suivre le format établi
3. Inclure des exemples d'utilisation
4. Documenter les cas d'usage
5. Tester le prompt avant de l'ajouter

---

## Ressources Complémentaires

- [Documentation FilAgent](README.md)
- [Guide de Contribution](CONTRIBUTING.md)
- [Standards de Code](docs/coding-standards.md)
- [Gouvernance LLM](docs/llm-governance.md)

---

*Dernière mise à jour: Décembre 2025*
*Mainteneur: fil04331*
