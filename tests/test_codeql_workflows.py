"""
Tests de validation des workflows CodeQL pour FilAgent.

Ce module vérifie que les workflows CodeQL sont correctement configurés
pour analyser le code Python de FilAgent.
"""

import pytest
import yaml
from pathlib import Path


class TestCodeQLWorkflows:
    """Tests de validation de la configuration CodeQL."""

    @pytest.fixture
    def workflows_dir(self):
        """Chemin vers le répertoire des workflows."""
        return Path(__file__).parent.parent / ".github" / "workflows"

    @pytest.fixture
    def codeql_workflow(self, workflows_dir):
        """Charge le workflow CodeQL principal."""
        workflow_path = workflows_dir / "codeql.yml"
        with open(workflow_path, "r") as f:
            return yaml.safe_load(f)

    @pytest.fixture
    def codeql_security_workflow(self, workflows_dir):
        """Charge le workflow CodeQL de sécurité."""
        workflow_path = workflows_dir / "codeql-security.yml"
        with open(workflow_path, "r") as f:
            return yaml.safe_load(f)

    def test_codeql_workflow_exists(self, workflows_dir):
        """Vérifie que le workflow CodeQL principal existe."""
        workflow_path = workflows_dir / "codeql.yml"
        assert workflow_path.exists(), "Le workflow codeql.yml doit exister"

    def test_codeql_security_workflow_exists(self, workflows_dir):
        """Vérifie que le workflow CodeQL de sécurité existe."""
        workflow_path = workflows_dir / "codeql-security.yml"
        assert workflow_path.exists(), "Le workflow codeql-security.yml doit exister"

    def test_codeql_workflow_has_required_triggers(self, codeql_workflow):
        """Vérifie que le workflow a les déclencheurs requis."""
        # YAML peut parser 'on:' comme True (boolean),
        # on doit chercher la clé True ou 'on'
        triggers = None
        if "on" in codeql_workflow:
            triggers = codeql_workflow["on"]
        elif True in codeql_workflow:
            triggers = codeql_workflow[True]

        assert triggers is not None, "Le workflow doit avoir des déclencheurs (on:)"

        # Vérifier push et pull_request
        assert "push" in triggers, "Le workflow doit se déclencher sur push"
        assert "pull_request" in triggers, "Le workflow doit se déclencher sur PR"

        # Vérifier schedule
        assert "schedule" in triggers, "Le workflow doit avoir un scan programmé"

    def test_codeql_workflow_targets_python(self, codeql_workflow):
        """Vérifie que le workflow cible Python."""
        jobs = codeql_workflow.get("jobs", {})
        analyze_job = jobs.get("analyze", {})
        strategy = analyze_job.get("strategy", {})
        matrix = strategy.get("matrix", {})

        # Chercher 'python' dans la configuration matrix
        found_python = False
        if "include" in matrix:
            for item in matrix["include"]:
                if item.get("language") == "python":
                    found_python = True
                    break
        elif "language" in matrix:
            languages = matrix["language"]
            if isinstance(languages, list):
                found_python = "python" in languages
            else:
                found_python = languages == "python"

        assert found_python, "Le workflow doit cibler Python"

    def test_codeql_workflow_installs_dependencies(self, codeql_workflow):
        """Vérifie que le workflow installe les dépendances."""
        jobs = codeql_workflow.get("jobs", {})
        analyze_job = jobs.get("analyze", {})
        steps = analyze_job.get("steps", [])

        # Chercher une étape qui installe requirements.txt
        found_install = False
        for step in steps:
            if "run" in step:
                run_cmd = step["run"]
                if "requirements.txt" in run_cmd and "pip install" in run_cmd:
                    found_install = True
                    break

        assert found_install, "Le workflow doit installer requirements.txt"

    def test_codeql_workflows_use_consistent_python_version(
        self, codeql_workflow, codeql_security_workflow
    ):
        """Vérifie que les deux workflows utilisent la même version de Python."""

        def get_python_version(workflow):
            jobs = workflow.get("jobs", {})
            analyze_job = jobs.get("analyze", {})
            steps = analyze_job.get("steps", [])

            for step in steps:
                if "uses" in step and "setup-python" in step["uses"]:
                    with_config = step.get("with", {})
                    return with_config.get("python-version")
            return None

        version1 = get_python_version(codeql_workflow)
        version2 = get_python_version(codeql_security_workflow)

        assert version1 is not None, "Le workflow codeql.yml doit définir une version Python"
        assert (
            version2 is not None
        ), "Le workflow codeql-security.yml doit définir une version Python"

        # Normaliser les versions pour comparaison (3.12 == '3.12')
        v1_str = str(version1)
        v2_str = str(version2)

        assert v1_str == v2_str, (
            f"Les workflows doivent utiliser la même version Python "
            f"(trouvé: {v1_str} vs {v2_str})"
        )

    def test_codeql_security_workflow_has_advanced_queries(self, codeql_security_workflow):
        """Vérifie que le workflow de sécurité utilise des queries avancées."""
        jobs = codeql_security_workflow.get("jobs", {})
        analyze_job = jobs.get("analyze", {})
        steps = analyze_job.get("steps", [])

        found_advanced_queries = False
        for step in steps:
            if "uses" in step and "codeql-action/init" in step["uses"]:
                with_config = step.get("with", {})
                queries = with_config.get("queries", "")
                if "security" in queries or "quality" in queries:
                    found_advanced_queries = True
                    break

        assert found_advanced_queries, (
            "Le workflow de sécurité doit utiliser des queries avancées " "(security-and-quality)"
        )

    def test_codeql_security_workflow_has_custom_checks(self, codeql_security_workflow):
        """Vérifie que le workflow de sécurité a des vérifications personnalisées."""
        jobs = codeql_security_workflow.get("jobs", {})
        analyze_job = jobs.get("analyze", {})
        steps = analyze_job.get("steps", [])

        # Chercher une étape avec des vérifications de sécurité personnalisées
        found_custom_checks = False
        for step in steps:
            step_name = step.get("name", "")
            if "Security" in step_name or "Sécurité" in step_name:
                if "run" in step:
                    run_cmd = step["run"]
                    # Vérifier la présence de checks pour secrets ou sandbox
                    if "secret" in run_cmd.lower() or "sandbox" in run_cmd.lower():
                        found_custom_checks = True
                        break

        assert found_custom_checks, (
            "Le workflow de sécurité doit avoir des vérifications personnalisées "
            "(détection de secrets, validation sandbox)"
        )

    def test_codeql_workflow_build_mode_is_none(self, codeql_workflow):
        """Vérifie que le build mode est 'none' pour Python."""
        jobs = codeql_workflow.get("jobs", {})
        analyze_job = jobs.get("analyze", {})
        strategy = analyze_job.get("strategy", {})
        matrix = strategy.get("matrix", {})

        # Chercher build-mode dans matrix.include
        if "include" in matrix:
            for item in matrix["include"]:
                if item.get("language") == "python":
                    build_mode = item.get("build-mode")
                    assert build_mode == "none", (
                        f"Le build mode pour Python doit être 'none', " f"trouvé: {build_mode}"
                    )

    def test_python_files_exist_in_critical_directories(self):
        """Vérifie que les répertoires critiques contiennent du code Python."""
        critical_dirs = ["runtime", "tools", "memory", "planner"]
        repo_root = Path(__file__).parent.parent

        for dir_name in critical_dirs:
            dir_path = repo_root / dir_name
            if dir_path.exists():
                py_files = list(dir_path.rglob("*.py"))
                assert (
                    len(py_files) > 0
                ), f"Le répertoire {dir_name}/ doit contenir des fichiers Python"


class TestCodeQLCoverage:
    """Tests de couverture du code par CodeQL."""

    def test_all_python_directories_are_analyzed(self):
        """
        Vérifie que les workflows CodeQL analyseront tous les répertoires Python.

        Note: Comme aucun filtre 'paths' n'est défini dans les workflows,
        tous les fichiers Python du repository sont analysés par défaut.
        """
        repo_root = Path(__file__).parent.parent
        workflows_dir = repo_root / ".github" / "workflows"

        # Charger les workflows
        for workflow_file in ["codeql.yml", "codeql-security.yml"]:
            workflow_path = workflows_dir / workflow_file
            with open(workflow_path, "r") as f:
                workflow = yaml.safe_load(f)

            # Gérer le fait que YAML peut parser 'on:' comme True
            triggers = workflow.get("on") or workflow.get(True, {})

            # Pour push
            if isinstance(triggers.get("push"), dict):
                assert "paths" not in triggers["push"], (
                    f"{workflow_file}: Ne devrait pas avoir de restriction 'paths' "
                    "pour analyser tout le code Python"
                )

            # Pour pull_request
            if isinstance(triggers.get("pull_request"), dict):
                assert "paths" not in triggers["pull_request"], (
                    f"{workflow_file}: Ne devrait pas avoir de restriction 'paths' "
                    "pour analyser tout le code Python"
                )
