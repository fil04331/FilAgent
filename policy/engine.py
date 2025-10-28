"""
Policy enforcement engine

Enforces security policies, RBAC, resource limits, and guardrails.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional


class PolicyEngine:
    """Enforces policies from config/policies.yaml"""
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = "config/policies.yaml"
        
        self.config_path = Path(config_path)
        self.policies = self._load_policies()
    
    def _load_policies(self) -> Dict:
        """Load policies from YAML"""
        if not self.config_path.exists():
            # Return default policies if file doesn't exist
            return self._get_default_policies()
        
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception:
            return self._get_default_policies()
    
    def _get_default_policies(self) -> Dict:
        """Get default policies"""
        return {
            "policies": {
                "rbac": {
                    "roles": [
                        {
                            "name": "admin",
                            "permissions": [
                                "read_all_logs",
                                "manage_config",
                                "execute_all_tools",
                                "view_audit"
                            ]
                        },
                        {
                            "name": "user",
                            "permissions": [
                                "execute_safe_tools",
                                "read_own_logs",
                                "manage_own_data"
                            ]
                        },
                        {
                            "name": "viewer",
                            "permissions": [
                                "read_own_logs"
                            ]
                        }
                    ]
                },
                "tools": {
                    "allowlist": ["python_sandbox", "file_read", "math_calculator"],
                    "network_access": {"enabled": False, "allowed_domains": []},
                    "filesystem": {
                        "allowed_paths": ["working_set/*", "temp/*", "memory/working_set/*"]
                    },
                    "resource_limits": {
                        "cpu_percent": 50,
                        "memory_mb": 512,
                        "max_file_size_kb": 1024
                    }
                },
                "network": {
                    "outbound_enabled": False,
                    "allowed_ips": [],
                    "block_external": True
                },
                "guardrails": {
                    "enabled": True,
                    "max_prompt_length": 8000,
                    "max_response_length": 4000,
                    "blocklist_keywords": ["password", "secret_key", "api_key"]
                }
            }
        }
    
    def has_permission(self, role: str, permission: str) -> bool:
        """Check if role has permission"""
        roles = self.policies.get("policies", {}).get("rbac", {}).get("roles", [])
        
        for role_def in roles:
            if role_def.get("name") == role:
                return permission in role_def.get("permissions", [])
        
        return False
    
    def is_tool_allowed(self, tool_name: str) -> bool:
        """Check if tool is in allowlist"""
        allowlist = self.policies.get("policies", {}).get("tools", {}).get("allowlist", [])
        return tool_name in allowlist
    
    def is_network_allowed(self) -> bool:
        """Check if network access is allowed"""
        return self.policies.get("policies", {}).get("network", {}).get("outbound_enabled", False)
    
    def is_domain_allowed(self, domain: str) -> bool:
        """Check if domain is in allowed list"""
        allowed_domains = self.policies.get("policies", {}).get("tools", {}).get("network_access", {}).get("allowed_domains", [])
        return domain in allowed_domains
    
    def is_path_allowed(self, path: str) -> bool:
        """Check if file path is allowed"""
        allowed_patterns = self.policies.get("policies", {}).get("tools", {}).get("filesystem", {}).get("allowed_paths", [])
        
        # Check if path matches any allowed pattern
        for pattern in allowed_patterns:
            if pattern.endswith("/*"):
                prefix = pattern[:-2]
                if path.startswith(prefix):
                    return True
            elif path == pattern:
                return True
        
        return False
    
    def get_resource_limit(self, resource_type: str) -> Optional[int]:
        """Get resource limit"""
        limits = self.policies.get("policies", {}).get("tools", {}).get("resource_limits", {})
        return limits.get(resource_type)
    
    def contains_blocked_keyword(self, text: str) -> bool:
        """Check if text contains blocked keywords"""
        keywords = self.policies.get("policies", {}).get("guardrails", {}).get("blocklist_keywords", [])
        
        text_lower = text.lower()
        for keyword in keywords:
            if keyword.lower() in text_lower:
                return True
        
        return False
    
    def get_max_prompt_length(self) -> int:
        """Get maximum prompt length"""
        return self.policies.get("policies", {}).get("guardrails", {}).get("max_prompt_length", 8000)
    
    def get_max_response_length(self) -> int:
        """Get maximum response length"""
        return self.policies.get("policies", {}).get("guardrails", {}).get("max_response_length", 4000)
    
    def is_prompt_valid(self, prompt: str) -> bool:
        """Check if prompt is valid"""
        max_length = self.get_max_prompt_length()
        return len(prompt) <= max_length
    
    def is_response_valid(self, response: str) -> bool:
        """Check if response is valid"""
        max_length = self.get_max_response_length()
        return len(response) <= max_length
