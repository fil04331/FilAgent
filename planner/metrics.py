"""
Module de métriques Prometheus pour HTN Planning

Exporte les métriques HTN pour monitoring via Prometheus:
- Adoption du HTN (usage rate)
- Performance (temps d'exécution)
- Parallélisation (taux de tâches parallèles)
- Fiabilité (taux de succès)
- Vérification (taux de validation)

Usage:
    from planner.metrics import HTNMetrics
    metrics = HTNMetrics()
    metrics.record_planning(...)
"""

from typing import Optional
import threading

# Try to import prometheus_client, but make it optional
try:
    from prometheus_client import Counter, Histogram, Gauge, Summary, Info

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

    # Stub classes pour compatibilité sans prometheus
    class Counter:
        def __init__(self, *args, **kwargs):
            pass

        def inc(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

    class Histogram:
        def __init__(self, *args, **kwargs):
            pass

        def observe(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

        def time(self, *args, **kwargs):
            return self

    class Gauge:
        def __init__(self, *args, **kwargs):
            pass

        def set(self, *args, **kwargs):
            pass

        def inc(self, *args, **kwargs):
            pass

        def dec(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

    class Summary:
        def __init__(self, *args, **kwargs):
            pass

        def observe(self, *args, **kwargs):
            pass

    class Info:
        def __init__(self, *args, **kwargs):
            pass

        def info(self, *args, **kwargs):
            pass


class HTNMetrics:
    """
    Collecteur de métriques HTN pour Prometheus

    Métriques collectées:
    1. htn_requests_total: Nombre total de requêtes HTN
    2. htn_planning_duration_seconds: Durée de planification
    3. htn_execution_duration_seconds: Durée d'exécution
    4. htn_tasks_total: Nombre total de tâches
    5. htn_tasks_completed_total: Tâches complétées
    6. htn_tasks_failed_total: Tâches échouées
    7. htn_tasks_parallel_total: Tâches exécutées en parallèle
    8. htn_verification_pass_rate: Taux de réussite des vérifications
    9. htn_planning_strategy_usage: Usage des stratégies
    10. htn_execution_strategy_usage: Usage des stratégies d'exécution
    """

    def __init__(self, enabled: bool = True):
        """
        Initialise le collecteur de métriques

        Args:
            enabled: Active la collecte de métriques
        """
        self.enabled = enabled and PROMETHEUS_AVAILABLE

        if not self.enabled:
            # Mode désactivé ou prometheus non disponible
            return

        # === Métriques Planning ===

        # Compteur: Requêtes HTN totales
        self.htn_requests_total = Counter(
            "htn_requests_total",
            "Total number of HTN planning requests",
            ["strategy", "status"],  # strategy: rule_based, llm_based, hybrid
        )

        # Histogram: Durée de planification
        self.htn_planning_duration_seconds = Histogram(
            "htn_planning_duration_seconds",
            "Time spent planning HTN tasks",
            ["strategy"],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
        )

        # Gauge: Confiance de planification
        self.htn_planning_confidence = Gauge(
            "htn_planning_confidence", "Confidence score of HTN planning", ["strategy"]
        )

        # === Métriques Execution ===

        # Histogram: Durée d'exécution
        self.htn_execution_duration_seconds = Histogram(
            "htn_execution_duration_seconds",
            "Time spent executing HTN tasks",
            ["strategy"],  # strategy: sequential, parallel, adaptive
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
        )

        # Compteur: Tâches complétées
        self.htn_tasks_completed_total = Counter(
            "htn_tasks_completed_total",
            "Total number of completed HTN tasks",
            ["priority", "action", "status"],
        )

        # Compteur: Tâches échouées
        self.htn_tasks_failed_total = Counter(
            "htn_tasks_failed_total",
            "Total number of failed HTN tasks",
            ["priority", "action", "error_type"],
        )

        # Compteur: Tâches en parallèle
        self.htn_tasks_parallel_total = Counter(
            "htn_tasks_parallel_total", "Total number of tasks executed in parallel", ["strategy"]
        )

        # Gauge: Tâches en cours
        self.htn_tasks_in_progress = Gauge(
            "htn_tasks_in_progress", "Number of HTN tasks currently in progress", ["strategy"]
        )

        # === Métriques Verification ===

        # Compteur: Vérifications totales
        self.htn_verifications_total = Counter(
            "htn_verifications_total",
            "Total number of HTN task verifications",
            ["level", "status"],  # level: basic, strict, paranoid
        )

        # Gauge: Taux de réussite des vérifications
        self.htn_verification_pass_rate = Gauge(
            "htn_verification_pass_rate", "Pass rate of HTN task verifications", ["level"]
        )

        # === Métriques Globales ===

        # Info: Version et configuration
        self.htn_info = Info("htn_info", "HTN planning module information")
        self.htn_info.info({"version": "1.0.0", "module": "planner"})

        # Gauge: Métriques calculées (pour dashboards)
        self.htn_usage_rate = Gauge("htn_usage_rate", "Percentage of requests using HTN planning")

        self.htn_success_rate = Gauge(
            "htn_success_rate", "Success rate of HTN plans (completed/total)"
        )

        self.htn_parallelization_factor = Gauge(
            "htn_parallelization_factor", "Percentage of tasks executed in parallel"
        )

    def record_planning(
        self,
        strategy: str,
        success: bool,
        duration_seconds: float,
        confidence: float,
        tasks_count: int = 0,
    ):
        """
        Enregistre une métrique de planification

        Args:
            strategy: Stratégie utilisée (rule_based, llm_based, hybrid)
            success: True si planification réussie
            duration_seconds: Durée de planification
            confidence: Score de confiance (0-1)
            tasks_count: Nombre de tâches créées
        """
        if not self.enabled:
            return

        status = "success" if success else "failure"
        self.htn_requests_total.labels(strategy=strategy, status=status).inc()
        self.htn_planning_duration_seconds.labels(strategy=strategy).observe(duration_seconds)
        self.htn_planning_confidence.labels(strategy=strategy).set(confidence)

    def record_execution(
        self,
        strategy: str,
        success: bool,
        duration_seconds: float,
        completed_tasks: int,
        failed_tasks: int,
        skipped_tasks: int,
        parallel_tasks: int = 0,
    ):
        """
        Enregistre une métrique d'exécution

        Args:
            strategy: Stratégie d'exécution (sequential, parallel, adaptive)
            success: True si exécution réussie
            duration_seconds: Durée d'exécution
            completed_tasks: Nombre de tâches complétées
            failed_tasks: Nombre de tâches échouées
            skipped_tasks: Nombre de tâches sautées
            parallel_tasks: Nombre de tâches exécutées en parallèle
        """
        if not self.enabled:
            return

        self.htn_execution_duration_seconds.labels(strategy=strategy).observe(duration_seconds)

        if parallel_tasks > 0:
            self.htn_tasks_parallel_total.labels(strategy=strategy).inc(parallel_tasks)

    def record_task(
        self,
        priority: str,
        action: str,
        status: str,
        error_type: Optional[str] = None,
    ):
        """
        Enregistre une métrique de tâche

        Args:
            priority: Priorité de la tâche (critical, high, normal, low, optional)
            action: Action de la tâche
            status: Statut (completed, failed, skipped)
            error_type: Type d'erreur si échec
        """
        if not self.enabled:
            return

        if status == "completed":
            self.htn_tasks_completed_total.labels(
                priority=priority, action=action, status=status
            ).inc()
        elif status == "failed":
            error_type = error_type or "unknown"
            self.htn_tasks_failed_total.labels(
                priority=priority, action=action, error_type=error_type
            ).inc()

    def record_verification(
        self,
        level: str,
        passed: bool,
        confidence_score: float = 1.0,
    ):
        """
        Enregistre une métrique de vérification

        Args:
            level: Niveau de vérification (basic, strict, paranoid)
            passed: True si vérification réussie
            confidence_score: Score de confiance (0-1)
        """
        if not self.enabled:
            return

        status = "passed" if passed else "failed"
        self.htn_verifications_total.labels(level=level, status=status).inc()

    def update_task_in_progress(self, strategy: str, count: int):
        """
        Met à jour le nombre de tâches en cours

        Args:
            strategy: Stratégie d'exécution
            count: Nombre de tâches en cours
        """
        if not self.enabled:
            return

        self.htn_tasks_in_progress.labels(strategy=strategy).set(count)

    def update_computed_metrics(
        self,
        usage_rate: float,
        success_rate: float,
        parallelization_factor: float,
        verification_pass_rate: float,
    ):
        """
        Met à jour les métriques calculées

        Args:
            usage_rate: Taux d'usage HTN (0-1)
            success_rate: Taux de succès (0-1)
            parallelization_factor: Facteur de parallélisation (0-1)
            verification_pass_rate: Taux de réussite des vérifications (0-1)
        """
        if not self.enabled:
            return

        self.htn_usage_rate.set(usage_rate)
        self.htn_success_rate.set(success_rate)
        self.htn_parallelization_factor.set(parallelization_factor)
        # Note: verification_pass_rate calculé séparément via PromQL


# Instance globale (singleton)
_metrics_instance: Optional[HTNMetrics] = None
_metrics_lock = threading.RLock()


def get_metrics(enabled: bool = True) -> HTNMetrics:
    """
    Récupère l'instance globale de métriques (thread-safe)

    Args:
        enabled: Active la collecte de métriques

    Returns:
        Instance HTNMetrics
    """
    global _metrics_instance

    if _metrics_instance is None:
        with _metrics_lock:  # Double-checked locking
            if _metrics_instance is None:
                _metrics_instance = HTNMetrics(enabled=enabled)

    return _metrics_instance


def reset_metrics():
    """Réinitialise l'instance de métriques (utile pour tests)"""
    global _metrics_instance
    with _metrics_lock:
        _metrics_instance = None
