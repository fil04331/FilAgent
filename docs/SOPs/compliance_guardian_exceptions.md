# SOP – Gestion des exceptions ComplianceGuardian

## 1. Quand déclencher la procédure ?

Activez cette procédure lorsque :

* un plan HTN est bloqué par le `ComplianceGuardian` en **mode strict**,
* la tâche répond à une exigence métier urgente documentée,
* aucune alternative sécuritaire (réécriture du plan, découpage, outil approuvé) n'est disponible.

## 2. Check-list immédiate

1. **Identifier l'alerte**
   * Relever le message d'erreur complet (voir les métadonnées `compliance_guardian_error`).
   * Exporter le rapport JSON écrit dans le log de planification.
2. **Vérifier la légitimité**
   * Confirmer avec le Product Owner que la tâche est prioritaire.
   * Contrôler que l'action ne viole pas les politiques internes (sécurité, RGPD, Loi 25).
3. **Tracer la demande**
   * Créer un ticket dans l'outil de suivi (Jira/Linear) avec le label `compliance-exception`.
   * Joindre les extraits de logs et le plan HTN généré.

## 3. Processus d'exception

| Étape | Responsable | Détails |
| --- | --- | --- |
| Analyse du risque | Security Champion | Évalue l'impact et propose des mitigations (sandbox renforcé, DR manuel). |
| Validation métier | Product Owner | Confirme la nécessité, ajuste la portée si besoin. |
| Approbation finale | DPO ou Compliance Officer | Autorise explicitement l'exception pour une durée limitée. |

> **Important :** aucune désactivation globale de `strict_mode` n'est autorisée en production. Les exceptions doivent être ciblées (plan ou conversation) et tracées.

## 4. Mise en œuvre du contournement

1. **Créer un Decision Record** (`logs/decisions/`) détaillant : contexte, risques, mesures compensatoires, durée de validité.
2. **Appliquer un override temporaire**
   * Injecter un paramètre de contournement côté workflow (p. ex. `plan.metadata["compliance_override"] = "ticket-123"`).
   * Mettre à jour la configuration runtime (feature flag, allow-list d'action) *sans* modifier `config/agent.yaml`.
3. **Déployer un monitoring renforcé**
   * Activer les métriques Prometheus `htn_planning_confidence` et `htn_compliance_overrides_total`.
   * Ajouter un audit manuel en fin de journée.

## 5. Clôture et rétroaction

* Annuler l'override dès que la tâche est terminée.
* Mettre à jour le ticket avec les résultats et les éventuels incidents.
* Programmer un post-mortem si l'exception dure > 72h ou si un incident est détecté.
* Proposer des améliorations (nouveaux garde-fous, automatisation des checklists) pour éviter la répétition.

## 6. Références

* `config/agent.yaml` – section `compliance_guardian` pour les paramètres globaux.
* `tests/test_planner/test_planner_stress.py` – validation de charge et du mode strict.
* `docs/ADR/` (s'il existe) – référentiel des décisions précédentes.

