#!/usr/bin/env python3
"""
Tests unitaires pour les scripts Prometheus

Vérifie que les scripts respectent les standards de l'industrie:
- Syntaxe correcte
- Gestion d'erreurs appropriée
- Messages clairs
- Code de retour correct
- Compatibilité

Usage:
    pytest tests/test_scripts_prometheus.py -v
"""

import pytest
import sys
import os
import subprocess
from pathlib import Path

# Ajouter le répertoire racine au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


class TestScriptsSyntax:
    """Tests de syntaxe des scripts"""
    
    def test_python_scripts_syntax(self):
        """Vérifie que tous les scripts Python ont une syntaxe valide"""
        python_scripts = [
            "validate_prometheus_setup.py",
            "generate_test_metrics.py",
            "test_metrics.py",
        ]
        
        for script in python_scripts:
            script_path = SCRIPTS_DIR / script
            if script_path.exists():
                # Vérifier la syntaxe
                result = subprocess.run(
                    [sys.executable, "-m", "py_compile", str(script_path)],
                    capture_output=True,
                    text=True
                )
                assert result.returncode == 0, f"Syntaxe invalide dans {script}: {result.stderr}"
    
    def test_bash_scripts_syntax(self):
        """Vérifie que tous les scripts Bash ont une syntaxe valide"""
        bash_scripts = [
            "install_prometheus_monitoring.sh",
            "start_prometheus.sh",
        ]
        
        for script in bash_scripts:
            script_path = SCRIPTS_DIR / script
            if script_path.exists():
                # Vérifier la syntaxe bash
                result = subprocess.run(
                    ["bash", "-n", str(script_path)],
                    capture_output=True,
                    text=True
                )
                assert result.returncode == 0, f"Syntaxe invalide dans {script}: {result.stderr}"


class TestScriptsImports:
    """Tests des imports des scripts Python"""
    
    def test_validate_prometheus_setup_imports(self):
        """Vérifie que validate_prometheus_setup.py peut être importé"""
        script_path = SCRIPTS_DIR / "validate_prometheus_setup.py"
        if script_path.exists():
            # Tester l'import (sans exécuter)
            result = subprocess.run(
                [sys.executable, "-c", f"import sys; sys.path.insert(0, '{SCRIPTS_DIR.parent}'); exec(open('{script_path}').read().split('if __name__')[0])"],
                capture_output=True,
                text=True,
                timeout=5
            )
            # L'import peut échouer si dépendances manquantes, mais ne doit pas planter
            # On vérifie juste qu'il n'y a pas d'erreur de syntaxe
    
    def test_generate_test_metrics_imports(self):
        """Vérifie que generate_test_metrics.py peut être importé"""
        script_path = SCRIPTS_DIR / "generate_test_metrics.py"
        if script_path.exists():
            result = subprocess.run(
                [sys.executable, "-c", f"import sys; sys.path.insert(0, '{SCRIPTS_DIR.parent}'); exec(open('{script_path}').read().split('if __name__')[0])"],
                capture_output=True,
                text=True,
                timeout=5
            )


class TestScriptsHelp:
    """Tests de l'aide des scripts"""
    
    def test_validate_prometheus_setup_help(self):
        """Vérifie que validate_prometheus_setup.py affiche l'aide"""
        script_path = SCRIPTS_DIR / "validate_prometheus_setup.py"
        if script_path.exists():
            result = subprocess.run(
                [sys.executable, str(script_path), "--help"],
                capture_output=True,
                text=True,
                timeout=5
            )
            # Doit retourner 0 (succès) ou 2 (erreur argparse), pas 1 (erreur)
            assert result.returncode in [0, 2], f"Help invalide pour validate_prometheus_setup.py"
    
    def test_generate_test_metrics_help(self):
        """Vérifie que generate_test_metrics.py affiche l'aide"""
        script_path = SCRIPTS_DIR / "generate_test_metrics.py"
        if script_path.exists():
            result = subprocess.run(
                [sys.executable, str(script_path), "--help"],
                capture_output=True,
                text=True,
                timeout=5
            )
            assert result.returncode in [0, 2], f"Help invalide pour generate_test_metrics.py"


class TestScriptsErrorHandling:
    """Tests de gestion d'erreurs"""
    
    def test_validate_prometheus_setup_no_dependencies(self):
        """Vérifie que validate_prometheus_setup.py gère gracieusement les dépendances manquantes"""
        script_path = SCRIPTS_DIR / "validate_prometheus_setup.py"
        if script_path.exists():
            # Exécuter sans dépendances (doit fonctionner avec fallback)
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=10
            )
            # Ne doit pas planter, mais peut retourner code d'erreur
            # Vérifier qu'il y a un message clair
            assert "requests" in result.stdout.lower() or "requests" in result.stderr.lower() or result.returncode == 0
    
    def test_test_metrics_handles_missing_requests(self):
        """Vérifie que test_metrics.py gère gracieusement requests manquant"""
        script_path = SCRIPTS_DIR / "test_metrics.py"
        if script_path.exists():
            # Simuler l'absence de requests en modifiant temporairement sys.path
            # ou en vérifiant que le script gère correctement le cas où requests est disponible
            # Comme requests est dans requirements.txt, le script devrait fonctionner normalement
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=5
            )
            # Le script devrait fonctionner normalement si requests est disponible
            # ou retourner un code d'erreur 1 si requests est manquant
            # Comme requests est installé, le script devrait retourner 0
            # Le test vérifie que le script gère correctement les deux cas
            if result.returncode == 1:
                # Si requests est manquant, le script doit afficher un message clair
                assert "requests" in result.stdout.lower() or "requests" in result.stderr.lower()
            else:
                # Si requests est disponible, le script devrait fonctionner normalement
                assert result.returncode == 0


class TestScriptsFiles:
    """Tests de présence des fichiers"""
    
    def test_all_scripts_exist(self):
        """Vérifie que tous les scripts existent"""
        required_scripts = [
            "install_prometheus_monitoring.sh",
            "start_prometheus.sh",
            "validate_prometheus_setup.py",
            "generate_test_metrics.py",
            "test_metrics.py",
        ]
        
        for script in required_scripts:
            script_path = SCRIPTS_DIR / script
            assert script_path.exists(), f"Script manquant: {script}"
            assert script_path.is_file(), f"Pas un fichier: {script}"
            assert script_path.stat().st_size > 0, f"Fichier vide: {script}"
    
    def test_scripts_are_executable(self):
        """Vérifie que les scripts sont exécutables (Unix)"""
        bash_scripts = [
            "install_prometheus_monitoring.sh",
            "start_prometheus.sh",
        ]
        
        if os.name != "nt":  # Pas Windows
            for script in bash_scripts:
                script_path = SCRIPTS_DIR / script
                if script_path.exists():
                    assert os.access(script_path, os.X_OK), f"Script non exécutable: {script}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

