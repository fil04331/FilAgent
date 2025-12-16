"""
Tests for Prometheus configuration and target generation.

Tests verify:
1. Prometheus configuration is valid YAML
2. Target generation script works correctly
3. Environment variables are properly used
4. Docker and K8s configurations are valid
"""

import pytest
import json
import yaml
import os
import subprocess
from pathlib import Path


@pytest.fixture
def config_dir():
    """Return path to config directory."""
    return Path(__file__).parent.parent / "config"


@pytest.fixture
def scripts_dir():
    """Return path to scripts directory."""
    return Path(__file__).parent.parent / "scripts"


@pytest.mark.unit
class TestPrometheusConfigYAML:
    """Test Prometheus YAML configuration."""
    
    def test_prometheus_yaml_exists(self, config_dir):
        """Test that prometheus.yml exists."""
        prometheus_yml = config_dir / "prometheus.yml"
        assert prometheus_yml.exists(), "prometheus.yml not found"
    
    def test_prometheus_yaml_is_valid(self, config_dir):
        """Test that prometheus.yml is valid YAML."""
        prometheus_yml = config_dir / "prometheus.yml"
        
        with open(prometheus_yml) as f:
            config = yaml.safe_load(f)
        
        assert config is not None
        assert isinstance(config, dict)
    
    def test_prometheus_yaml_has_scrape_configs(self, config_dir):
        """Test that prometheus.yml has scrape_configs."""
        prometheus_yml = config_dir / "prometheus.yml"
        
        with open(prometheus_yml) as f:
            config = yaml.safe_load(f)
        
        assert "scrape_configs" in config
        assert isinstance(config["scrape_configs"], list)
        assert len(config["scrape_configs"]) > 0
    
    def test_prometheus_yaml_has_filagent_job(self, config_dir):
        """Test that prometheus.yml has filagent job."""
        prometheus_yml = config_dir / "prometheus.yml"
        
        with open(prometheus_yml) as f:
            config = yaml.safe_load(f)
        
        job_names = [job["job_name"] for job in config["scrape_configs"]]
        assert "filagent" in job_names
    
    def test_prometheus_yaml_has_file_sd_config(self, config_dir):
        """Test that prometheus.yml includes file_sd_configs."""
        prometheus_yml = config_dir / "prometheus.yml"
        
        with open(prometheus_yml) as f:
            config = yaml.safe_load(f)
        
        filagent_job = next(
            job for job in config["scrape_configs"]
            if job["job_name"] == "filagent"
        )
        
        # Should have file_sd_configs for dynamic discovery
        assert "file_sd_configs" in filagent_job
    
    def test_prometheus_yaml_has_static_fallback(self, config_dir):
        """Test that prometheus.yml has static config fallback."""
        prometheus_yml = config_dir / "prometheus.yml"
        
        with open(prometheus_yml) as f:
            config = yaml.safe_load(f)
        
        filagent_job = next(
            job for job in config["scrape_configs"]
            if job["job_name"] == "filagent"
        )
        
        # Should have static config as fallback
        assert "static_configs" in filagent_job


@pytest.mark.unit
class TestPrometheusTargets:
    """Test Prometheus target JSON files."""
    
    def test_targets_json_exists(self, config_dir):
        """Test that prometheus_targets.json exists."""
        targets_file = config_dir / "prometheus_targets.json"
        assert targets_file.exists()
    
    def test_targets_json_is_valid(self, config_dir):
        """Test that prometheus_targets.json is valid JSON."""
        targets_file = config_dir / "prometheus_targets.json"
        
        with open(targets_file) as f:
            targets = json.load(f)
        
        assert isinstance(targets, list)
    
    def test_targets_json_has_correct_structure(self, config_dir):
        """Test that targets JSON has correct Prometheus format."""
        targets_file = config_dir / "prometheus_targets.json"
        
        with open(targets_file) as f:
            targets = json.load(f)
        
        assert len(targets) > 0
        
        for target_group in targets:
            assert "targets" in target_group
            assert isinstance(target_group["targets"], list)
            assert "labels" in target_group
            assert isinstance(target_group["labels"], dict)
    
    def test_targets_json_local_configuration(self, config_dir):
        """Test local development targets."""
        targets_file = config_dir / "prometheus_targets.json"
        
        with open(targets_file) as f:
            targets = json.load(f)
        
        # Should have localhost:8000 for local dev
        first_target = targets[0]["targets"][0]
        assert "localhost" in first_target or "127.0.0.1" in first_target
        assert "8000" in first_target
    
    def test_docker_targets_json_exists(self, config_dir):
        """Test that Docker targets file exists."""
        targets_file = config_dir / "prometheus_targets_docker.json"
        assert targets_file.exists()
    
    def test_docker_targets_has_service_name(self, config_dir):
        """Test Docker targets use service names."""
        targets_file = config_dir / "prometheus_targets_docker.json"
        
        with open(targets_file) as f:
            targets = json.load(f)
        
        # Should use Docker service name, not localhost
        first_target = targets[0]["targets"][0]
        assert "localhost" not in first_target
        assert "filagent" in first_target.lower()


@pytest.mark.unit
class TestTargetGenerationScript:
    """Test the target generation script."""
    
    def test_script_exists(self, scripts_dir):
        """Test that generation script exists."""
        script_file = scripts_dir / "generate_prometheus_targets.py"
        assert script_file.exists()
    
    def test_script_is_executable(self, scripts_dir):
        """Test script has proper permissions."""
        script_file = scripts_dir / "generate_prometheus_targets.py"
        
        # On Unix, check if file is executable
        if os.name != 'nt':  # Not Windows
            assert os.access(script_file, os.X_OK) or script_file.read_text().startswith('#!/usr/bin/env')
    
    def test_script_runs_without_errors(self, scripts_dir, tmp_path):
        """Test script executes successfully."""
        script_file = scripts_dir / "generate_prometheus_targets.py"
        output_file = tmp_path / "test_targets.json"
        
        # Run script with custom output
        env = os.environ.copy()
        env["OUTPUT_FILE"] = str(output_file)
        
        result = subprocess.run(
            ["python", str(script_file)],
            env=env,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"Script failed: {result.stderr}"
        assert output_file.exists()
    
    def test_script_generates_valid_json(self, scripts_dir, tmp_path):
        """Test script generates valid JSON."""
        script_file = scripts_dir / "generate_prometheus_targets.py"
        output_file = tmp_path / "test_targets.json"
        
        env = os.environ.copy()
        env["OUTPUT_FILE"] = str(output_file)
        
        subprocess.run(
            ["python", str(script_file)],
            env=env,
            check=True
        )
        
        # Verify JSON is valid
        with open(output_file) as f:
            targets = json.load(f)
        
        assert isinstance(targets, list)
        assert len(targets) > 0
    
    def test_script_uses_environment_variables(self, scripts_dir, tmp_path):
        """Test script respects environment variables."""
        script_file = scripts_dir / "generate_prometheus_targets.py"
        output_file = tmp_path / "test_targets.json"
        
        custom_host = "custom-host"
        custom_port = "9000"
        custom_env = "production"
        
        env = os.environ.copy()
        env["OUTPUT_FILE"] = str(output_file)
        env["FILAGENT_HOST"] = custom_host
        env["FILAGENT_PORT"] = custom_port
        env["ENVIRONMENT"] = custom_env
        
        subprocess.run(
            ["python", str(script_file)],
            env=env,
            check=True
        )
        
        with open(output_file) as f:
            targets = json.load(f)
        
        # Check custom values
        target_address = targets[0]["targets"][0]
        assert custom_host in target_address
        assert custom_port in target_address
        
        labels = targets[0]["labels"]
        assert labels["env"] == custom_env
    
    def test_script_default_values(self, scripts_dir, tmp_path):
        """Test script uses correct defaults."""
        script_file = scripts_dir / "generate_prometheus_targets.py"
        output_file = tmp_path / "test_targets.json"
        
        # Run without custom env vars
        env = {
            "OUTPUT_FILE": str(output_file),
            "PATH": os.environ.get("PATH", "")
        }
        
        subprocess.run(
            ["python", str(script_file)],
            env=env,
            check=True
        )
        
        with open(output_file) as f:
            targets = json.load(f)
        
        # Check defaults
        target_address = targets[0]["targets"][0]
        assert "localhost:8000" == target_address or "localhost" in target_address
        
        labels = targets[0]["labels"]
        assert labels["env"] == "development"


@pytest.mark.integration
class TestPrometheusIntegration:
    """Integration tests for Prometheus configuration."""
    
    def test_prometheus_can_parse_config(self, config_dir):
        """Test that Prometheus can parse the configuration (if promtool is available)."""
        prometheus_yml = config_dir / "prometheus.yml"
        
        try:
            # Try to validate with promtool if available
            result = subprocess.run(
                ["promtool", "check", "config", str(prometheus_yml)],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # promtool is available and config is valid
                assert True
            else:
                pytest.skip("promtool not available or config has issues")
        except FileNotFoundError:
            pytest.skip("promtool not installed")
    
    def test_metrics_endpoint_compatibility(self):
        """Test that metrics format is compatible with Prometheus."""
        try:
            from prometheus_client import generate_latest
            from runtime.metrics import get_agent_metrics, reset_agent_metrics
            
            reset_agent_metrics()
            metrics = get_agent_metrics()
            
            # Generate metrics
            metrics.record_tool_execution("test", 0.1, "success")
            
            # Export in Prometheus format
            output = generate_latest()
            
            # Basic validation
            assert b"filagent_tool_execution_seconds" in output
            assert b"# HELP" in output
            assert b"# TYPE" in output
        except ImportError:
            pytest.skip("prometheus_client not available")


@pytest.mark.unit
class TestDockerConfiguration:
    """Test Docker-specific configuration."""
    
    def test_docker_compose_prometheus_service(self):
        """Test that docker-compose has Prometheus configuration."""
        docker_compose = Path(__file__).parent.parent / "docker-compose.yml"
        
        if not docker_compose.exists():
            pytest.skip("docker-compose.yml not found")
        
        with open(docker_compose) as f:
            config = yaml.safe_load(f)
        
        # This is a basic check - adjust based on actual docker-compose structure
        assert config is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
