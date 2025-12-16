#!/usr/bin/env python3
"""
Generate Prometheus target configuration from environment variables.

This script allows dynamic Prometheus configuration in containerized environments
without requiring Prometheus restart.

Usage:
    # Local development
    python scripts/generate_prometheus_targets.py

    # Docker environment
    FILAGENT_HOST=filagent-api ENVIRONMENT=docker python scripts/generate_prometheus_targets.py

    # Kubernetes environment
    FILAGENT_HOST=filagent-service.filagent.svc.cluster.local ENVIRONMENT=k8s python scripts/generate_prometheus_targets.py

Environment Variables:
    FILAGENT_HOST: Hostname/IP of FilAgent API (default: localhost)
    FILAGENT_PORT: Port of FilAgent API (default: 8000)
    ENVIRONMENT: Environment name (default: development)
    OUTPUT_FILE: Output file path (default: config/prometheus_targets.json)
"""

import json
import os
from pathlib import Path


def generate_targets():
    """Generate Prometheus targets configuration from environment variables."""
    host = os.getenv("FILAGENT_HOST", "localhost")
    port = os.getenv("FILAGENT_PORT", "8000")
    environment = os.getenv("ENVIRONMENT", "development")
    output_file = os.getenv("OUTPUT_FILE", "config/prometheus_targets.json")
    
    # Build target address
    target = f"{host}:{port}"
    
    # Create target configuration
    targets_config = [
        {
            "targets": [target],
            "labels": {
                "env": environment,
                "service": "filagent-api",
                "job": "filagent",
            }
        }
    ]
    
    # Ensure output directory exists
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write configuration
    with open(output_path, "w") as f:
        json.dump(targets_config, f, indent=2)
    
    print(f"✓ Generated Prometheus targets: {output_path}")
    print(f"  Target: {target}")
    print(f"  Environment: {environment}")


if __name__ == "__main__":
    generate_targets()
