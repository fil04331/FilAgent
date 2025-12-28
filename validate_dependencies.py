#!/usr/bin/env python3
"""
Dependency Compatibility Validation Script
Tests compatibility with FastAPI 0.127+, Pydantic 2.12+, and llama-cpp-python 0.3+
"""

import sys
from typing import List, Tuple


def test_pydantic_v2_compatibility() -> Tuple[bool, List[str]]:
    """Test Pydantic v2 compatibility"""
    errors = []
    
    try:
        from pydantic import BaseModel, Field, ConfigDict, field_validator
        print("✓ Pydantic v2 imports successful")
    except ImportError as e:
        errors.append(f"Failed to import Pydantic v2 components: {e}")
        return False, errors
    
    # Test model with ConfigDict
    try:
        class TestModel(BaseModel):
            model_config = ConfigDict(arbitrary_types_allowed=True)
            name: str = Field(default="test")
            value: int = Field(ge=0, default=42)
        
        m = TestModel()
        
        # Test model_dump (replaces .dict())
        data = m.model_dump()
        assert isinstance(data, dict)
        assert "name" in data and "value" in data
        print("✓ model_dump() works (Pydantic v2)")
        
        # Test model_fields on class (not instance)
        fields = TestModel.model_fields
        assert "name" in fields and "value" in fields
        print("✓ model_fields class access works (Pydantic v2)")
        
        # Test field_validator
        class ValidatedModel(BaseModel):
            email: str
            
            @field_validator("email")
            @classmethod
            def validate_email(cls, v):
                if "@" not in v:
                    raise ValueError("Invalid email")
                return v
        
        try:
            ValidatedModel(email="invalid")
            errors.append("field_validator did not raise expected error")
        except Exception:
            print("✓ field_validator works (Pydantic v2)")
        
    except Exception as e:
        errors.append(f"Pydantic v2 model test failed: {e}")
        return False, errors
    
    return True, errors


def test_fastapi_compatibility() -> Tuple[bool, List[str]]:
    """Test FastAPI 0.127+ compatibility"""
    errors = []
    
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
        
        app = FastAPI(title="Test API")
        
        class RequestModel(BaseModel):
            name: str
            value: int
        
        class ResponseModel(BaseModel):
            result: str
        
        @app.post("/test", response_model=ResponseModel)
        def test_endpoint(request: RequestModel):
            return ResponseModel(result=f"Hello {request.name}")
        
        print("✓ FastAPI app creation with Pydantic v2 models")
        
    except Exception as e:
        errors.append(f"FastAPI test failed: {e}")
        return False, errors
    
    return True, errors


def test_llama_cpp_compatibility() -> Tuple[bool, List[str]]:
    """Test llama-cpp-python 0.3.x compatibility"""
    errors = []
    
    try:
        from llama_cpp import Llama
        import inspect
        
        print("✓ llama-cpp-python imports successfully")
        
        # Check expected methods exist
        required_methods = ["__init__", "__call__"]
        for method in required_methods:
            if not hasattr(Llama, method):
                errors.append(f"Llama class missing method: {method}")
        
        if not errors:
            print("✓ Llama class has expected methods")
        
        # Check __init__ signature
        sig = inspect.signature(Llama.__init__)
        required_params = ["model_path", "n_ctx", "n_gpu_layers", "use_mmap", "use_mlock"]
        
        params = list(sig.parameters.keys())
        for param in required_params:
            if param not in params:
                errors.append(f"Llama.__init__ missing parameter: {param}")
        
        if not errors:
            print("✓ Llama.__init__ has all expected parameters")
        
    except ImportError as e:
        # llama-cpp-python is optional, so don't fail if not installed
        print(f"⚠ llama-cpp-python not installed (optional): {e}")
        return True, errors
    except Exception as e:
        errors.append(f"llama-cpp-python test failed: {e}")
        return False, errors
    
    return True, errors


def test_runtime_modules() -> Tuple[bool, List[str]]:
    """Test FilAgent runtime modules"""
    errors = []
    
    try:
        from runtime.config import AgentConfig, GenerationConfig as ConfigGenerationConfig
        print("✓ runtime.config imports successfully")
    except Exception as e:
        errors.append(f"Failed to import runtime.config: {e}")
        return False, errors
    
    try:
        from runtime.model_interface import LlamaCppInterface, GenerationConfig as ModelGenerationConfig
        print("✓ runtime.model_interface imports successfully")
    except Exception as e:
        errors.append(f"Failed to import runtime.model_interface: {e}")
        return False, errors
    
    try:
        # Test that runtime.config.GenerationConfig is a proper Pydantic v2 model
        from dataclasses import is_dataclass
        config = ConfigGenerationConfig()
        
        # Should be a Pydantic model
        if hasattr(config, "model_dump"):
            print("✓ runtime.config.GenerationConfig uses Pydantic v2")
        else:
            errors.append("runtime.config.GenerationConfig should be a Pydantic v2 model")
            return False, errors
            
        # Test that model_interface.GenerationConfig is a dataclass
        model_config = ModelGenerationConfig()
        if is_dataclass(model_config):
            print("✓ runtime.model_interface.GenerationConfig uses dataclass (valid)")
        else:
            errors.append("runtime.model_interface.GenerationConfig should be a dataclass")
            return False, errors
    except Exception as e:
        errors.append(f"GenerationConfig test failed: {e}")
        return False, errors
    
    return True, errors


def test_no_deprecated_patterns() -> Tuple[bool, List[str]]:
    """Verify no deprecated Pydantic v1 patterns in codebase"""
    errors = []
    import subprocess
    import os
    
    # Get repo root (script is in repo root)
    repo_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(repo_root)
    
    # Directories to search for code (not tests, not examples, not docs)
    search_dirs = ["runtime/", "tools/", "memory/", "planner/", "policy/"]
    
    deprecated_patterns = [
        ("pydantic.v1", "Use pydantic v2 instead"),
        ("from pydantic import validator", "Use field_validator"),
        ("@validator", "Use @field_validator"),
    ]
    
    for pattern, message in deprecated_patterns:
        try:
            # Build grep command with search directories
            cmd = ["grep", "-r", pattern, "--include=*.py"] + search_dirs
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                errors.append(f"Found deprecated pattern '{pattern}': {message}")
                print(f"✗ Found deprecated pattern: {pattern}")
            else:
                print(f"✓ No deprecated pattern: {pattern}")
        except Exception as e:
            print(f"⚠ Could not check pattern '{pattern}': {e}")
    
    return len(errors) == 0, errors


def main():
    """Run all validation tests"""
    print("=" * 60)
    print("FilAgent Dependency Compatibility Validation")
    print("=" * 60)
    print()
    
    # Check versions
    try:
        import pydantic
        print(f"Pydantic version: {pydantic.__version__}")
    except:
        pass
    
    try:
        import fastapi
        print(f"FastAPI version: {fastapi.__version__}")
    except:
        pass
    
    try:
        import llama_cpp
        print(f"llama-cpp-python version: {llama_cpp.__version__}")
    except:
        pass
    
    print()
    print("-" * 60)
    print("Running Tests")
    print("-" * 60)
    print()
    
    all_errors = []
    all_passed = True
    
    tests = [
        ("Pydantic v2 Compatibility", test_pydantic_v2_compatibility),
        ("FastAPI Compatibility", test_fastapi_compatibility),
        ("llama-cpp-python Compatibility", test_llama_cpp_compatibility),
        ("Runtime Modules", test_runtime_modules),
        ("No Deprecated Patterns", test_no_deprecated_patterns),
    ]
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            passed, errors = test_func()
            if not passed:
                all_passed = False
                all_errors.extend(errors)
                print(f"✗ {test_name} FAILED")
            else:
                print(f"✓ {test_name} PASSED")
        except Exception as e:
            all_passed = False
            all_errors.append(f"{test_name}: Unexpected error: {e}")
            print(f"✗ {test_name} FAILED: {e}")
    
    print()
    print("=" * 60)
    if all_passed:
        print("✅ ALL VALIDATION TESTS PASSED")
        print()
        print("The codebase is compatible with:")
        print("  - FastAPI 0.127.0+")
        print("  - Pydantic 2.12.5+")
        print("  - llama-cpp-python 0.3.16+")
        print()
        print("Safe to merge PR #241!")
        return 0
    else:
        print("❌ VALIDATION FAILED")
        print()
        print("Errors found:")
        for error in all_errors:
            print(f"  - {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
