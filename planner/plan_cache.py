"""
Cache LRU pour Plans HTN

Implemente un cache LRU (Least Recently Used) pour memoriser les plans HTN
frequemment utilises, ameliorant significativement les performances pour
requetes repetees.

Standards:
- Thread-safe avec threading.RLock()
- LRU algorithm standard (collections.OrderedDict)
- Metriques Prometheus pour monitoring
- Configuration via config/agent.yaml

Usage:
    cache = PlanCache(max_size=100, ttl_seconds=3600)
    cache_key = cache.get_key(query, strategy, context)

    # Chercher dans le cache
    cached_plan = cache.get(cache_key)
    if cached_plan:
        return cached_plan

    # Creer et mettre en cache
    plan = planner.plan(query, strategy, context)
    cache.put(cache_key, plan)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Union
from datetime import datetime
from collections import OrderedDict
import threading
import hashlib
import json

from .metrics import get_metrics

if TYPE_CHECKING:
    from .planner import PlanningResult, PlanningStrategy


# Type aliases for strict typing
ContextDict = Dict[str, Union[str, int, float, bool, List[str], Dict[str, str]]]
StatsDict = Dict[str, Union[int, float, Optional[int]]]


@dataclass
class CacheEntry:
    """Entree de cache pour un plan"""
    plan_result: PlanningResult
    cached_at: datetime
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)

    def is_expired(self, ttl_seconds: Optional[int]) -> bool:
        """Verifie si l'entree est expiree"""
        if ttl_seconds is None:
            return False

        age = (datetime.now() - self.cached_at).total_seconds()
        return age > ttl_seconds


class PlanCache:
    """
    Cache LRU pour plans HTN

    Caracteristiques:
    - LRU (Least Recently Used) avec taille maximale
    - Thread-safe pour utilisation concurrente
    - TTL optionnel pour expiration automatique
    - Metriques Prometheus pour monitoring
    - Hash de requete pour identification unique

    Standards:
    - LRU algorithm: collections.OrderedDict
    - Thread safety: threading.RLock()
    - Monitoring: Prometheus metrics
    """

    def __init__(
        self,
        max_size: int = 100,
        ttl_seconds: Optional[int] = None,
        enable_metrics: bool = True,
    ) -> None:
        """
        Initialise le cache

        Args:
            max_size: Taille maximale du cache (nombre d'entrees)
            ttl_seconds: TTL en secondes (None = pas d'expiration)
            enable_metrics: Active metriques Prometheus
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.enable_metrics = enable_metrics

        # Cache LRU: OrderedDict (plus recent a la fin)
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()

        # Thread safety
        self._lock = threading.RLock()

        # Statistiques
        self._stats: Dict[str, int] = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
            "sets": 0,
        }

        # Metriques
        self.metrics = get_metrics() if enable_metrics else None

    def get_key(
        self,
        query: str,
        strategy: PlanningStrategy,
        context: Optional[ContextDict] = None,
    ) -> str:
        """
        Genere une cle de cache unique pour une requete

        Args:
            query: Requete utilisateur
            strategy: Strategie de planification
            context: Contexte additionnel (optionnel)

        Returns:
            Hash SHA256 de la requete + strategie + contexte
        """
        # Normaliser la requete (lowercase, strip)
        normalized_query = query.lower().strip()

        # Creer un dict pour hash coherent
        cache_data: Dict[str, Union[str, ContextDict]] = {
            "query": normalized_query,
            "strategy": getattr(strategy, 'value', str(strategy)),  # Support string ou enum
            "context": self._normalize_context(context) if context else {},
        }

        # Serialiser en JSON (ordre garanti en Python 3.7+)
        json_str = json.dumps(cache_data, sort_keys=True, ensure_ascii=False)

        # Hash SHA256
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()

    def _normalize_context(self, context: ContextDict) -> ContextDict:
        """Normalise le contexte pour hash coherent"""
        # Retirer les champs non pertinents pour le cache
        # (conversation_id, task_id changent mais n'affectent pas le plan)
        normalized: ContextDict = {}

        # Garder seulement les champs pertinents pour la planification
        relevant_fields = [
            "max_depth",
            "constraints",
            "preferences",
            # Ajouter d'autres champs pertinents si necessaire
        ]

        for key in relevant_fields:
            if key in context:
                normalized[key] = context[key]

        return normalized

    def get(
        self,
        cache_key: str,
    ) -> Optional[PlanningResult]:
        """
        Recupere un plan depuis le cache

        Args:
            cache_key: Cle de cache

        Returns:
            PlanningResult si trouve et non expire, None sinon
        """
        with self._lock:
            # Chercher dans le cache
            if cache_key not in self._cache:
                self._stats["misses"] += 1
                self._record_metrics("miss")
                return None

            entry = self._cache[cache_key]

            # Verifier expiration
            if entry.is_expired(self.ttl_seconds):
                del self._cache[cache_key]
                self._stats["expirations"] += 1
                self._stats["misses"] += 1
                self._record_metrics("miss")
                self._record_metrics("expiration")
                return None

            # Hit: deplacer a la fin (plus recent)
            self._cache.move_to_end(cache_key)

            # Mettre a jour statistiques
            entry.access_count += 1
            entry.last_accessed = datetime.now()

            self._stats["hits"] += 1
            self._record_metrics("hit")

            return entry.plan_result

    def put(
        self,
        cache_key: str,
        plan_result: PlanningResult,
    ) -> None:
        """
        Met un plan en cache

        Args:
            cache_key: Cle de cache
            plan_result: Resultat de planification a mettre en cache
        """
        with self._lock:
            # Creer l'entree
            entry = CacheEntry(
                plan_result=plan_result,
                cached_at=datetime.now(),
                access_count=0,
                last_accessed=datetime.now(),
            )

            # Si la cle existe deja, remplacer
            if cache_key in self._cache:
                # Mettre a jour a la fin (plus recent)
                self._cache[cache_key] = entry
                self._cache.move_to_end(cache_key)
            else:
                # Nouvelle entree
                # Si cache plein, evincer LRU (premiere entree = moins recent)
                if len(self._cache) >= self.max_size:
                    self._cache.popitem(last=False)  # Retirer le plus ancien
                    self._stats["evictions"] += 1
                    self._record_metrics("eviction")

                # Ajouter a la fin
                self._cache[cache_key] = entry

            self._stats["sets"] += 1
            self._record_metrics("set")

    def invalidate(self, cache_key: Optional[str] = None) -> None:
        """
        Invalide une entree ou tout le cache

        Args:
            cache_key: Cle a invalider (None = tout le cache)
        """
        with self._lock:
            if cache_key is None:
                # Vider tout le cache
                self._cache.clear()
            else:
                # Invalider une cle specifique
                if cache_key in self._cache:
                    del self._cache[cache_key]

    def clear_expired(self) -> None:
        """Supprime toutes les entrees expirees"""
        if self.ttl_seconds is None:
            return  # Pas de TTL

        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired(self.ttl_seconds)
            ]

            # BUG FIX: Incrementer le compteur une seule fois en dehors de la boucle
            num_expired = len(expired_keys)
            if num_expired > 0:
                self._stats["expirations"] += num_expired
                self._record_metrics("expiration")

            # Supprimer les entrees expirees
            for key in expired_keys:
                del self._cache[key]

    def get_stats(self) -> StatsDict:
        """Retourne les statistiques du cache"""
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (
                self._stats["hits"] / total_requests
                if total_requests > 0 else 0.0
            )

            return {
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate": hit_rate,
                "evictions": self._stats["evictions"],
                "expirations": self._stats["expirations"],
                "sets": self._stats["sets"],
                "current_size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds,
            }

    def _record_metrics(self, event: str) -> None:
        """Enregistre les metriques Prometheus"""
        if not self.metrics or not hasattr(self.metrics, 'record_plan_cache'):
            return

        try:
            self.metrics.record_plan_cache(
                event=event,
                cache_size=len(self._cache),
            )
        except Exception:
            # Ignorer les erreurs de metriques (ne pas casser le cache)
            pass


# Instance globale (singleton)
_cache_instance: Optional[PlanCache] = None
_cache_lock = threading.RLock()


def get_plan_cache(
    max_size: int = 100,
    ttl_seconds: Optional[int] = None,
    enable_metrics: bool = True,
) -> PlanCache:
    """
    Obtient ou cree l'instance globale du cache

    Args:
        max_size: Taille maximale (ignore si instance existe)
        ttl_seconds: TTL en secondes (ignore si instance existe)
        enable_metrics: Active metriques (ignore si instance existe)

    Returns:
        Instance PlanCache (singleton)
    """
    global _cache_instance

    with _cache_lock:
        if _cache_instance is None:
            _cache_instance = PlanCache(
                max_size=max_size,
                ttl_seconds=ttl_seconds,
                enable_metrics=enable_metrics,
            )

        return _cache_instance


def reset_plan_cache() -> None:
    """Reinitialise le cache global (utile pour tests)"""
    global _cache_instance

    with _cache_lock:
        _cache_instance = None
