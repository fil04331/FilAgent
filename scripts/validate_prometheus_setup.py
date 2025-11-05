#!/usr/bin/env python3
"""
Script de validation complète de l'installation Prometheus

Vérifie:
- Installation de prometheus-client
- Fichiers de configuration
- Serveur FilAgent accessible
- Endpoint /metrics fonctionnel
- Métriques HTN disponibles
- Prometheus accessible (optionnel)
- Alertes configurées (optionnel)

Usage:
    python3 scripts/validate_prometheus_setup.py [--check-prometheus] [--check-alerts]
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Import requests (optionnel, avec fallback)
try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Import yaml (optionnel, avec fallback)
try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# Ajouter le répertoire racine au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ValidationResult:
    """Résultat d'une validation"""

    def __init__(self, name: str, passed: bool, message: str = "", details: Dict = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details or {}

    def __repr__(self):
        status = "✅" if self.passed else "❌"
        return f"{status} {self.name}: {self.message}"


class PrometheusSetupValidator:
    """Validateur de l'installation Prometheus"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        self.results: List[ValidationResult] = []

    def validate(self, check_prometheus: bool = False, check_alerts: bool = False) -> bool:
        """Exécute toutes les validations"""
        print("=" * 70)
        print("VALIDATION DE L'INSTALLATION PROMETHEUS")
        print("=" * 70)
        print()

        # 1. Vérifications Python
        self.validate_python_dependencies()

        # 2. Vérifications fichiers
        self.validate_configuration_files()

        # 3. Vérifications module
        self.validate_metrics_module()

        # 4. Vérifications serveur
        self.validate_server_endpoint()

        # 5. Vérifications métriques
        self.validate_metrics_endpoint()

        # 6. Vérifications Prometheus (optionnel)
        if check_prometheus:
            self.validate_prometheus_connection()

        # 7. Vérifications alertes (optionnel)
        if check_alerts:
            self.validate_alert_rules()

        # Résumé
        return self.print_summary()

    def validate_python_dependencies(self):
        """Vérifie les dépendances Python"""
        print("📦 1. Vérification des dépendances Python...")
        print()

        # prometheus-client
        try:
            import prometheus_client

            version = prometheus_client.__version__
            self.results.append(
                ValidationResult(
                    "prometheus-client",
                    True,
                    f"Installé (version: {version})",
                    {"version": version},
                )
            )
        except ImportError:
            self.results.append(
                ValidationResult(
                    "prometheus-client",
                    False,
                    "Non installé. Installez avec: pip install prometheus-client",
                )
            )

        # requests (pour les tests)
        try:
            import requests

            self.results.append(ValidationResult("requests", True, "Installé"))
        except ImportError:
            self.results.append(
                ValidationResult("requests", False, "Non installé (requis pour les tests)")
            )

        print()

    def validate_configuration_files(self):
        """Vérifie les fichiers de configuration"""
        print("📋 2. Vérification des fichiers de configuration...")
        print()

        required_files = [
            ("config/prometheus.yml", "Configuration Prometheus"),
            ("config/prometheus_alerts.yml", "Règles d'alertes"),
            ("planner/metrics.py", "Module de métriques"),
            ("runtime/server.py", "Serveur FastAPI"),
        ]

        for file_path, description in required_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                # Vérifier que le fichier n'est pas vide
                size = full_path.stat().st_size
                self.results.append(
                    ValidationResult(file_path, True, f"{description} présent ({size} bytes)")
                )
            else:
                self.results.append(ValidationResult(file_path, False, f"{description} manquant"))

        print()

    def validate_metrics_module(self):
        """Vérifie que le module metrics peut être importé"""
        print("🔍 3. Vérification du module metrics...")
        print()

        try:
            from planner.metrics import HTNMetrics, get_metrics

            self.results.append(ValidationResult("planner.metrics", True, "Module importable"))

            # Test initialisation
            try:
                metrics = get_metrics(enabled=False)
                self.results.append(
                    ValidationResult("HTNMetrics initialization", True, "Initialisation réussie")
                )
            except Exception as e:
                self.results.append(
                    ValidationResult(
                        "HTNMetrics initialization", False, f"Erreur d'initialisation: {e}"
                    )
                )
        except ImportError as e:
            self.results.append(ValidationResult("planner.metrics", False, f"Erreur d'import: {e}"))

        print()

    def validate_server_endpoint(self):
        """Vérifie que le serveur FilAgent est accessible"""
        print("🌐 4. Vérification du serveur FilAgent...")
        print()

        if not REQUESTS_AVAILABLE:
            self.results.append(
                ValidationResult(
                    "Server /health",
                    False,
                    "Module 'requests' non disponible. Installez avec: pip install requests",
                )
            )
            return

        server_url = "http://localhost:8000"

        # Test endpoint /health
        try:
            response = requests.get(f"{server_url}/health", timeout=5)
            if response.status_code == 200:
                self.results.append(
                    ValidationResult(
                        "Server /health", True, f"Accessible (code {response.status_code})"
                    )
                )
            else:
                self.results.append(
                    ValidationResult(
                        "Server /health", False, f"Retourne code {response.status_code}"
                    )
                )
        except requests.exceptions.ConnectionError:
            self.results.append(
                ValidationResult(
                    "Server /health",
                    False,
                    "Serveur non accessible. Démarrez avec: python3 -m runtime.server",
                )
            )
        except Exception as e:
            self.results.append(ValidationResult("Server /health", False, f"Erreur: {e}"))

        print()

    def validate_metrics_endpoint(self):
        """Vérifie l'endpoint /metrics"""
        print("📊 5. Vérification de l'endpoint /metrics...")
        print()

        if not REQUESTS_AVAILABLE:
            self.results.append(
                ValidationResult(
                    "Endpoint /metrics",
                    False,
                    "Module 'requests' non disponible. Installez avec: pip install requests",
                )
            )
            return

        server_url = "http://localhost:8000"
        metrics_url = f"{server_url}/metrics"

        try:
            response = requests.get(metrics_url, timeout=5)

            if response.status_code == 200:
                content = response.text

                # Vérifier Content-Type
                content_type = response.headers.get("Content-Type", "")
                is_prometheus_format = (
                    "text/plain" in content_type or "prometheus" in content_type.lower()
                )

                self.results.append(
                    ValidationResult(
                        "Endpoint /metrics",
                        True,
                        f"Accessible (code {response.status_code})",
                        {"content_type": content_type, "size": len(content)},
                    )
                )

                # Vérifier présence métriques HTN
                htn_metrics = [
                    "htn_requests_total",
                    "htn_planning_duration_seconds",
                    "htn_execution_duration_seconds",
                    "htn_tasks_completed_total",
                    "htn_tasks_failed_total",
                    "htn_verifications_total",
                ]

                found_metrics = [m for m in htn_metrics if m in content]

                if found_metrics:
                    self.results.append(
                        ValidationResult(
                            "Métriques HTN",
                            True,
                            f"{len(found_metrics)}/{len(htn_metrics)} métriques trouvées",
                            {"found": found_metrics},
                        )
                    )
                else:
                    self.results.append(
                        ValidationResult(
                            "Métriques HTN",
                            False,
                            "Aucune métrique HTN trouvée (normal si aucune requête HTN n'a été exécutée)",
                        )
                    )

            else:
                self.results.append(
                    ValidationResult(
                        "Endpoint /metrics", False, f"Retourne code {response.status_code}"
                    )
                )

        except requests.exceptions.ConnectionError:
            self.results.append(
                ValidationResult("Endpoint /metrics", False, "Serveur non accessible")
            )
        except Exception as e:
            self.results.append(ValidationResult("Endpoint /metrics", False, f"Erreur: {e}"))

        print()

    def validate_prometheus_connection(self):
        """Vérifie la connexion à Prometheus"""
        print("🔍 6. Vérification de la connexion Prometheus...")
        print()

        if not REQUESTS_AVAILABLE:
            self.results.append(
                ValidationResult(
                    "Prometheus API",
                    False,
                    "Module 'requests' non disponible. Installez avec: pip install requests",
                )
            )
            return

        prometheus_url = "http://localhost:9090"

        try:
            # Test endpoint /api/v1/query
            response = requests.get(
                f"{prometheus_url}/api/v1/query", params={"query": "up"}, timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    self.results.append(
                        ValidationResult("Prometheus API", True, "Accessible et fonctionnel")
                    )
                else:
                    self.results.append(
                        ValidationResult(
                            "Prometheus API", False, f"Retourne status: {data.get('status')}"
                        )
                    )
            else:
                self.results.append(
                    ValidationResult(
                        "Prometheus API", False, f"Retourne code {response.status_code}"
                    )
                )

        except requests.exceptions.ConnectionError:
            self.results.append(
                ValidationResult(
                    "Prometheus API",
                    False,
                    "Prometheus non accessible. Démarrez avec: ./scripts/start_prometheus.sh",
                )
            )
        except Exception as e:
            self.results.append(ValidationResult("Prometheus API", False, f"Erreur: {e}"))

        print()

    def validate_alert_rules(self):
        """Vérifie les règles d'alertes"""
        print("🚨 7. Vérification des règles d'alertes...")
        print()

        if not YAML_AVAILABLE:
            self.results.append(
                ValidationResult(
                    "YAML module",
                    False,
                    "Module yaml non disponible. Installez avec: pip install pyyaml",
                )
            )
            return

        alerts_file = self.project_root / "config/prometheus_alerts.yml"

        if not alerts_file.exists():
            self.results.append(
                ValidationResult(
                    "Alert rules file", False, "Fichier prometheus_alerts.yml non trouvé"
                )
            )
            return

        try:
            with open(alerts_file, "r") as f:
                alerts_config = yaml.safe_load(f)

            if not alerts_config or "groups" not in alerts_config:
                self.results.append(
                    ValidationResult(
                        "Alert rules format", False, "Format YAML invalide ou pas de groupes"
                    )
                )
                return

            groups = alerts_config.get("groups", [])
            total_alerts = sum(len(group.get("rules", [])) for group in groups)

            self.results.append(
                ValidationResult(
                    "Alert rules",
                    True,
                    f"{len(groups)} groupes, {total_alerts} règles",
                    {"groups": len(groups), "total_alerts": total_alerts},
                )
            )

        except yaml.YAMLError as e:
            self.results.append(
                ValidationResult("Alert rules YAML", False, f"Erreur de parsing YAML: {e}")
            )
        except Exception as e:
            self.results.append(ValidationResult("Alert rules", False, f"Erreur: {e}"))

        print()

    def print_summary(self) -> bool:
        """Affiche le résumé des validations"""
        print("=" * 70)
        print("RÉSUMÉ DE VALIDATION")
        print("=" * 70)
        print()

        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)

        for result in self.results:
            print(f"{result}")
            if result.details:
                for key, value in result.details.items():
                    print(f"   {key}: {value}")

        print()
        print("=" * 70)
        print(f"📊 Score: {passed}/{total} validations réussies ({passed*100//total}%)")
        print("=" * 70)

        if passed == total:
            print("\n✅ Toutes les validations ont réussi!")
            print("\n📊 Prochaines étapes:")
            print("   1. Générer des métriques de test:")
            print("      python3 scripts/generate_test_metrics.py")
            print("   2. Configurer Prometheus (si pas déjà fait):")
            print("      ./scripts/start_prometheus.sh")
            print("   3. Vérifier les métriques dans Prometheus:")
            print("      http://localhost:9090")
            return True
        else:
            failed = [r for r in self.results if not r.passed]
            print(f"\n⚠️  {len(failed)} validation(s) ont échoué:")
            for result in failed:
                print(f"   - {result.name}: {result.message}")
            print("\n💡 Actions recommandées:")
            print("   1. Installer les dépendances manquantes")
            print("   2. Vérifier les fichiers de configuration")
            print("   3. Démarrer le serveur FilAgent")
            return False


def main():
    """Point d'entrée principal"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Valide l'installation complète de Prometheus pour FilAgent"
    )

    parser.add_argument(
        "--check-prometheus", action="store_true", help="Vérifier la connexion à Prometheus"
    )

    parser.add_argument("--check-alerts", action="store_true", help="Vérifier les règles d'alertes")

    args = parser.parse_args()

    validator = PrometheusSetupValidator()
    success = validator.validate(
        check_prometheus=args.check_prometheus, check_alerts=args.check_alerts
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
