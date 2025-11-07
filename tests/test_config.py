import os
import unittest
from ruamel.yaml import YAML
from runtime.config import AgentConfig, reload_config

class TestConfigPersistence(unittest.TestCase):

    def setUp(self):
        """Set up a temporary config directory and file for testing."""
        self.config_dir = "tests/temp_config"
        self.config_path = os.path.join(self.config_dir, "agent.yaml")

        # Ensure the temp config directory exists and is clean
        os.makedirs(self.config_dir, exist_ok=True)
        if os.path.exists(self.config_path):
            os.remove(self.config_path)

        # Clean up dummy config from previous runs if it exists
        if os.path.exists("config/agent.yaml"):
            os.remove("config/agent.yaml")

    def tearDown(self):
        """Clean up the temporary config file and directory."""
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        if os.path.exists(self.config_dir):
            os.rmdir(self.config_dir)
        # Clean up dummy config file created by the test
        if os.path.exists("config/agent.yaml"):
            os.remove("config/agent.yaml")

    def test_config_save_and_reload_preserves_comments(self):
        """Test that saving and reloading preserves comments and structure."""
        yaml = YAML()
        initial_content = """
# Fichier de configuration principal
agent:
  name: initial_agent # Nom de l'agent
  version: 0.1.0
model:
  name: initial-model
"""
        with open(self.config_path, "w") as f:
            f.write(initial_content)

        # 1. Load the initial config
        config = AgentConfig.load(config_dir=self.config_dir)

        # 2. Modify the config object
        config.version = "1.2.3"
        config.model.name = "updated-model"

        # 3. Save the modified config
        config.save(self.config_path)

        # 4. Reload the raw content and check for preservation
        with open(self.config_path, 'r') as f:
            reloaded_content = f.read()

        self.assertIn("# Fichier de configuration principal", reloaded_content)
        self.assertIn("# Nom de l'agent", reloaded_content)

        # 5. Reload the config object and check values
        reloaded_config = AgentConfig.load(config_dir=self.config_dir)
        self.assertEqual(reloaded_config.version, "1.2.3")
        self.assertEqual(reloaded_config.model.name, "updated-model")

if __name__ == '__main__':
    unittest.main()
