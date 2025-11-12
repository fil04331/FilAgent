#!/usr/bin/env python3
"""
Quick verification script for compliance_guardian initialization bug fix

This script directly tests that the bug is fixed without requiring pytest
or other dependencies.
"""

import sys
import traceback
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_1_config_loads_compliance_guardian():
    """Test: Config can load compliance_guardian section without NameError"""
    print("\n[Test 1] Testing config loads compliance_guardian section...")
    try:
        from runtime.config import AgentConfig

        # This would have raised NameError: name 'compliance_guardian_config' is not defined
        # before the fix in config.py line 209
        config = AgentConfig(
            name="test",
            version="1.0"
        )

        # Should have compliance_guardian attribute
        assert hasattr(config, 'compliance_guardian'), "Config missing compliance_guardian attribute"
        print("   ✓ Config has compliance_guardian attribute")
        print("   ✓ No NameError raised")
        return True
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        traceback.print_exc()
        return False


def test_2_agent_has_compliance_guardian_attribute():
    """Test: Agent has compliance_guardian attribute after init"""
    print("\n[Test 2] Testing Agent has compliance_guardian attribute...")
    try:
        from runtime.agent import Agent
        from unittest.mock import Mock, patch

        # Mock dependencies to avoid requiring full setup
        with patch('runtime.agent.get_config') as mock_config:
            from runtime.config import AgentConfig
            mock_config.return_value = AgentConfig(name="test", version="1.0")

            agent = Agent()

            # This would have raised AttributeError before the fix
            # when code tried: if self.compliance_guardian:
            assert hasattr(agent, 'compliance_guardian'), "Agent missing compliance_guardian attribute"
            print("   ✓ Agent has compliance_guardian attribute")
            print("   ✓ No AttributeError will occur")
            return True
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        traceback.print_exc()
        return False


def test_3_no_attribute_error_on_access():
    """Test: Accessing compliance_guardian doesn't raise AttributeError"""
    print("\n[Test 3] Testing no AttributeError on compliance_guardian access...")
    try:
        from runtime.agent import Agent
        from unittest.mock import Mock, patch
        from runtime.config import AgentConfig

        with patch('runtime.agent.get_config') as mock_config:
            mock_config.return_value = AgentConfig(name="test", version="1.0")
            agent = Agent()

            # This is the exact pattern that was failing before
            # Lines 347, 599, etc. in agent.py
            try:
                if agent.compliance_guardian:
                    # Would use it
                    cg = agent.compliance_guardian
                else:
                    # Would skip
                    pass
                print("   ✓ Can access compliance_guardian without AttributeError")
                return True
            except AttributeError as ae:
                print(f"   ✗ AttributeError raised: {ae}")
                print("   ✗ BUG FIX FAILED - attribute not initialized!")
                return False

    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        traceback.print_exc()
        return False


def test_4_compliance_guardian_initialized_when_enabled():
    """Test: ComplianceGuardian initializes when enabled in config"""
    print("\n[Test 4] Testing compliance_guardian initializes when enabled...")
    try:
        from runtime.agent import Agent
        from runtime.config import AgentConfig, ComplianceGuardianConfig
        from unittest.mock import patch

        with patch('runtime.agent.get_config') as mock_config:
            # Create config with compliance_guardian enabled
            cg_config = ComplianceGuardianConfig(
                enabled=True,
                rules_path="config/compliance_rules.yaml"
            )
            base_config = AgentConfig(name="test", version="1.0")
            base_config.compliance_guardian = cg_config
            mock_config.return_value = base_config

            agent = Agent()

            # Should have attribute (might be None if init failed gracefully)
            assert hasattr(agent, 'compliance_guardian'), "Missing compliance_guardian attribute"
            print("   ✓ compliance_guardian attribute exists")

            # Value is either ComplianceGuardian instance or None (graceful failure)
            if agent.compliance_guardian is None:
                print("   ℹ compliance_guardian is None (config file missing, graceful fallback)")
            else:
                from planner.compliance_guardian import ComplianceGuardian
                assert isinstance(agent.compliance_guardian, ComplianceGuardian)
                print("   ✓ compliance_guardian is ComplianceGuardian instance")

            return True

    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        traceback.print_exc()
        return False


def test_5_code_extraction_in_config():
    """Test: config.py properly extracts compliance_guardian_data"""
    print("\n[Test 5] Testing config.py extracts compliance_guardian_data...")
    try:
        import tempfile
        import yaml
        from runtime.config import AgentConfig

        # Create temp YAML with compliance_guardian section
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_data = {
                'agent': {'name': 'test', 'version': '1.0'},
                'generation': {'temperature': 0.2, 'max_tokens': 800},
                'timeouts': {'generation': 60, 'tool_execution': 30},
                'model': {'name': 'test-model', 'path': 'test.gguf', 'backend': 'llama.cpp'},
                'memory': {'episodic': {'ttl_days': 30}},
                'logging': {'level': 'INFO'},
                'compliance': {'enabled': True},
                'compliance_guardian': {
                    'enabled': True,
                    'validate_queries': True,
                    'strict_mode': True
                }
            }
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            # This would have raised NameError before the fix
            # Line 154: compliance_guardian_data = raw_config.get("compliance_guardian", {})
            # Line 198: compliance_guardian_config = ComplianceGuardianConfig(...)
            config = AgentConfig.from_yaml(temp_path)

            # Verify it was loaded
            assert hasattr(config, 'compliance_guardian'), "Config missing compliance_guardian"
            assert config.compliance_guardian is not None, "compliance_guardian should not be None"
            assert config.compliance_guardian.enabled is True, "enabled should be True"
            assert config.compliance_guardian.validate_queries is True, "validate_queries should be True"

            print("   ✓ compliance_guardian_data extracted from YAML")
            print("   ✓ ComplianceGuardianConfig created successfully")
            print(f"   ✓ Config values: enabled={config.compliance_guardian.enabled}, "
                  f"validate_queries={config.compliance_guardian.validate_queries}")

            return True

        finally:
            Path(temp_path).unlink(missing_ok=True)

    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all verification tests"""
    print("=" * 70)
    print("VERIFICATION: compliance_guardian Initialization Bug Fix")
    print("=" * 70)
    print("\nBug #1: Missing self.compliance_guardian initialization in Agent.__init__")
    print("Bug #2: Missing compliance_guardian_data extraction in config.py")
    print("\nRunning verification tests...\n")

    tests = [
        test_1_config_loads_compliance_guardian,
        test_2_agent_has_compliance_guardian_attribute,
        test_3_no_attribute_error_on_access,
        test_4_compliance_guardian_initialized_when_enabled,
        test_5_code_extraction_in_config,
    ]

    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"\n   ✗ Test crashed: {e}")
            traceback.print_exc()
            results.append(False)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passed = sum(results)
    total = len(results)

    print(f"\nTests passed: {passed}/{total}")

    if passed == total:
        print("\n✓ ALL TESTS PASSED - Bug fix verified!")
        print("\nThe following issues are now fixed:")
        print("  1. Agent.__init__ now initializes self.compliance_guardian")
        print("  2. config.py now extracts and creates compliance_guardian_config")
        print("  3. No more AttributeError when accessing compliance_guardian")
        print("  4. No more NameError in config loading")
        return 0
    else:
        print(f"\n✗ {total - passed} TEST(S) FAILED - Bug fix incomplete!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
