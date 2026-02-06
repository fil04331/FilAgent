"""
Tests for Agent._requires_planning method

Tests pour vérifier la détection automatique des requêtes multi-étapes
qui nécessitent une planification HTN.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.agent import Agent


@pytest.fixture
def mock_config_htn_enabled():
    """Configuration mock avec HTN activé"""
    config = Mock()
    htn_planning = Mock()
    htn_planning.enabled = True
    config.htn_planning = htn_planning
    return config


@pytest.fixture
def mock_config_htn_disabled():
    """Configuration mock avec HTN désactivé"""
    config = Mock()
    htn_planning = Mock()
    htn_planning.enabled = False
    config.htn_planning = htn_planning
    return config


@pytest.fixture
def agent_with_planner(mock_config_htn_enabled):
    """Agent avec planificateur initialisé"""
    with patch("runtime.agent.get_config", return_value=mock_config_htn_enabled):
        with (
            patch("runtime.agent.get_logger"),
            patch("runtime.agent.get_dr_manager"),
            patch("runtime.agent.get_tracker"),
        ):
            agent = Agent(config=mock_config_htn_enabled)
            # Simuler un planificateur initialisé
            agent.planner = Mock()
            return agent


@pytest.fixture
def agent_without_planner(mock_config_htn_enabled):
    """Agent sans planificateur (non initialisé)"""
    with patch("runtime.agent.get_config", return_value=mock_config_htn_enabled):
        with (
            patch("runtime.agent.get_logger"),
            patch("runtime.agent.get_dr_manager"),
            patch("runtime.agent.get_tracker"),
        ):
            agent = Agent(config=mock_config_htn_enabled)
            agent.planner = None
            return agent


class TestRequiresPlanning:
    """Tests pour la méthode _requires_planning"""

    def test_multi_step_keywords_puis(self, agent_with_planner):
        """Test détection du mot-clé 'puis'"""
        assert agent_with_planner._requires_planning("Lis le fichier puis analyse les données")

    def test_multi_step_keywords_ensuite(self, agent_with_planner):
        """Test détection du mot-clé 'ensuite'"""
        assert agent_with_planner._requires_planning("Crée un fichier, ensuite génère un rapport")

    def test_multi_step_keywords_apres(self, agent_with_planner):
        """Test détection du mot-clé 'après'"""
        assert agent_with_planner._requires_planning("Après avoir lu le fichier, calcule la somme")

    def test_multi_step_keywords_finalement(self, agent_with_planner):
        """Test détection du mot-clé 'finalement'"""
        assert agent_with_planner._requires_planning("D'abord lis, finalement affiche")

    def test_multi_step_keywords_et(self, agent_with_planner):
        """Test détection du mot-clé 'et'"""
        assert agent_with_planner._requires_planning("Lis le fichier et analyse les données")

    def test_multiple_action_verbs_french(self, agent_with_planner):
        """Test détection de plusieurs verbes d'action en français"""
        assert agent_with_planner._requires_planning("Lis le fichier, analyse les données")

    def test_multiple_action_verbs_english(self, agent_with_planner):
        """Test détection de plusieurs verbes d'action en anglais"""
        assert agent_with_planner._requires_planning("Read the file, analyze the data")

    def test_mixed_language_verbs(self, agent_with_planner):
        """Test détection avec verbes mixtes français/anglais"""
        assert agent_with_planner._requires_planning("Lis le fichier et generate a report")

    def test_single_action_verb(self, agent_with_planner):
        """Test qu'un seul verbe d'action ne déclenche pas HTN"""
        assert not agent_with_planner._requires_planning("Lis le fichier data.csv")

    def test_no_keywords_no_verbs(self, agent_with_planner):
        """Test sans mots-clés ni verbes d'action"""
        assert not agent_with_planner._requires_planning("Bonjour, comment ça va?")

    def test_htn_disabled_in_config(self):
        """Test que HTN est désactivé si config.htn_planning.enabled = False"""
        config = Mock()
        htn_planning = Mock()
        htn_planning.enabled = False
        config.htn_planning = htn_planning

        with patch("runtime.agent.get_config", return_value=config):
            with (
                patch("runtime.agent.get_logger"),
                patch("runtime.agent.get_dr_manager"),
                patch("runtime.agent.get_tracker"),
            ):
                agent = Agent(config=config)
                agent.planner = Mock()

                # Même avec mots-clés, HTN ne devrait pas être activé
                assert not agent._requires_planning("Lis le fichier puis analyse")

    def test_planner_not_initialized(self, agent_without_planner):
        """Test que HTN n'est pas utilisé si le planificateur n'est pas initialisé"""
        assert not agent_without_planner._requires_planning("Lis le fichier puis analyse")

    def test_case_insensitive_detection(self, agent_with_planner):
        """Test que la détection est insensible à la casse"""
        assert agent_with_planner._requires_planning("LIS le fichier PUIS ANALYSE")

    def test_genere_verb(self, agent_with_planner):
        """Test détection du verbe 'génère'"""
        query = "Lis le fichier et génère un rapport"
        assert agent_with_planner._requires_planning(query)

    def test_cree_verb(self, agent_with_planner):
        """Test détection du verbe 'crée'"""
        query = "Analyse les données et crée un graphique"
        assert agent_with_planner._requires_planning(query)

    def test_calcule_verb(self, agent_with_planner):
        """Test détection du verbe 'calcule'"""
        query = "Lis les nombres et calcule la moyenne"
        assert agent_with_planner._requires_planning(query)

    def test_create_verb_english(self, agent_with_planner):
        """Test détection du verbe 'create' en anglais"""
        query = "Read the file and create a summary"
        assert agent_with_planner._requires_planning(query)

    def test_calculate_verb_english(self, agent_with_planner):
        """Test détection du verbe 'calculate' en anglais"""
        query = "Read numbers and calculate average"
        assert agent_with_planner._requires_planning(query)

    def test_exactly_two_verbs(self, agent_with_planner):
        """Test que 2 verbes d'action déclenchent HTN"""
        query = "Lis le fichier et analyse"
        assert agent_with_planner._requires_planning(query)

    def test_three_or_more_verbs(self, agent_with_planner):
        """Test que 3+ verbes d'action déclenchent HTN"""
        query = "Lis le fichier, analyse les données et génère un rapport"
        assert agent_with_planner._requires_planning(query)

    def test_verb_in_middle_of_word(self, agent_with_planner):
        """Test qu'un verbe au milieu d'un mot est détecté (partiel)"""
        # Note: La méthode actuelle utilise 'in', donc cela détectera des faux positifs
        # mais c'est le comportement actuel
        query = "Utilise cet outil puis finalise"
        # "lis" est dans "Utilise", "analyse" n'y est pas
        # On devrait détecter "puis" comme mot-clé
        assert agent_with_planner._requires_planning(query)

    def test_empty_query(self, agent_with_planner):
        """Test avec requête vide"""
        assert not agent_with_planner._requires_planning("")

    def test_whitespace_only_query(self, agent_with_planner):
        """Test avec requête contenant uniquement des espaces"""
        assert not agent_with_planner._requires_planning("   ")

    def test_special_characters_in_query(self, agent_with_planner):
        """Test avec caractères spéciaux"""
        query = "Lis le fichier @data.csv puis analyse #tableau"
        assert agent_with_planner._requires_planning(query)

    def test_htn_config_none(self):
        """Test quand config.htn_planning est None"""
        config = Mock()
        config.htn_planning = None

        with patch("runtime.agent.get_config", return_value=config):
            with (
                patch("runtime.agent.get_logger"),
                patch("runtime.agent.get_dr_manager"),
                patch("runtime.agent.get_tracker"),
            ):
                agent = Agent(config=config)
                agent.planner = Mock()

                # Si htn_planning est None, enabled n'existe pas, donc devrait utiliser HTN
                assert agent._requires_planning("Lis puis analyse")

    def test_htn_config_missing_enabled_attribute(self):
        """Test quand config.htn_planning existe mais sans attribut 'enabled'"""
        config = Mock()
        htn_planning = Mock(spec=[])  # Mock sans attributs
        config.htn_planning = htn_planning

        with patch("runtime.agent.get_config", return_value=config):
            with (
                patch("runtime.agent.get_logger"),
                patch("runtime.agent.get_dr_manager"),
                patch("runtime.agent.get_tracker"),
            ):
                agent = Agent(config=config)
                agent.planner = Mock()

                # getattr avec default True devrait retourner True
                assert agent._requires_planning("Lis puis analyse")


class TestRequiresPlanningEdgeCases:
    """Tests de cas limites pour _requires_planning"""

    def test_unicode_characters(self, agent_with_planner):
        """Test avec caractères Unicode"""
        query = "Lis le fichier données.csv puis analyse les résultats"
        assert agent_with_planner._requires_planning(query)

    def test_numbers_in_query(self, agent_with_planner):
        """Test avec nombres dans la requête"""
        query = "Lis fichier1.csv, fichier2.csv et analyse"
        assert agent_with_planner._requires_planning(query)

    def test_newlines_in_query(self, agent_with_planner):
        """Test avec retours à la ligne"""
        query = "Lis le fichier\npuis analyse\nles données"
        assert agent_with_planner._requires_planning(query)

    def test_tabs_in_query(self, agent_with_planner):
        """Test avec tabulations"""
        query = "Lis\tle\tfichier\tpuis\tanalyse"
        assert agent_with_planner._requires_planning(query)

    def test_very_long_query(self, agent_with_planner):
        """Test avec requête très longue"""
        query = "Lis le fichier " * 100 + "puis analyse"
        assert agent_with_planner._requires_planning(query)

    def test_repeated_keywords(self, agent_with_planner):
        """Test avec mots-clés répétés"""
        query = "Lis puis lis puis lis puis analyse"
        assert agent_with_planner._requires_planning(query)

    def test_repeated_verbs(self, agent_with_planner):
        """Test avec verbes répétés"""
        query = "Lis le fichier et lis les données"
        assert agent_with_planner._requires_planning(query)

    def test_mixed_case_keywords(self, agent_with_planner):
        """Test avec mots-clés en casse mixte"""
        query = "LIS le fichier PUIS analyse LES données"
        assert agent_with_planner._requires_planning(query)

    def test_punctuation_around_keywords(self, agent_with_planner):
        """Test avec ponctuation autour des mots-clés"""
        query = "Lis le fichier, puis, analyse les données!"
        assert agent_with_planner._requires_planning(query)

    def test_html_tags_in_query(self, agent_with_planner):
        """Test avec balises HTML (cas d'injection)"""
        query = "Lis <script>alert()</script> puis analyse"
        assert agent_with_planner._requires_planning(query)


@pytest.mark.parametrize(
    "query,expected",
    [
        ("Lis le fichier", False),  # Single action
        ("Lis le fichier puis analyse", True),  # Multi-step
        ("Lis et analyse", True),  # Two actions
        ("Bonjour", False),  # No actions
        ("Read and analyze", True),  # English multi-step
        ("Read file", False),  # English single action
        ("Génère rapport", False),  # Single action
        ("Génère rapport et crée graphique", True),  # Two actions
        ("", False),  # Empty
        ("   ", False),  # Whitespace
    ],
)
def test_requires_planning_parametrized(query, expected, agent_with_planner):
    """Tests paramétrés pour _requires_planning"""
    assert agent_with_planner._requires_planning(query) == expected
