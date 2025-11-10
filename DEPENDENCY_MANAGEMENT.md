# Dependency Management Guide

This project uses modern Python dependency management with `pyproject.toml` (PEP 621).

## Quick Start

### Installation

```bash
# Basic installation
pip install -e .

# With development dependencies
pip install -e ".[dev]"

# With GPU support
pip install -e ".[gpu]"

# With full LLM support
pip install -e ".[llm-full]"

# All optional dependencies
pip install -e ".[dev,gpu,llm-full]"
```

### Using requirements.txt (Legacy)

For backward compatibility or CI/CD systems:

```bash
# Production dependencies
pip install -r requirements.txt

# Development dependencies
pip install -r requirements.txt -r requirements-dev.txt
```

## Dependency Files

### Primary Configuration

- **`pyproject.toml`** - Main dependency configuration (PEP 621 standard)
  - Contains all project metadata
  - Defines core and optional dependencies
  - Includes tool configurations (pytest, black, mypy, ruff)

### Legacy Files (maintained for compatibility)

- **`requirements.txt`** - Core dependencies with version constraints
- **`requirements-dev.txt`** - Development dependencies
- **`pytest.ini`** - Pytest configuration (now in pyproject.toml)

## Version Constraints

We use **compatible release constraints** to ensure stability:

- `>=X.Y.Z,<X+1.0.0` - Allow minor and patch updates, but not major versions
- Example: `pydantic>=2.5.0,<3.0.0` allows 2.5.0, 2.6.0, 2.99.9 but not 3.0.0

This prevents breaking changes while allowing bug fixes and new features.

## Advanced: Using pip-tools

For reproducible builds, consider using `pip-tools`:

### Setup

```bash
pip install pip-tools
```

### Create requirements.in

```bash
# requirements.in
-e .
```

### Compile locked versions

```bash
# Generate requirements.txt with pinned versions
pip-compile requirements.in

# Generate dev requirements
pip-compile --extra dev -o requirements-dev.txt pyproject.toml
```

### Sync environment

```bash
pip-sync requirements.txt requirements-dev.txt
```

### Update dependencies

```bash
# Update all dependencies
pip-compile --upgrade requirements.in

# Update specific package
pip-compile --upgrade-package pytest requirements.in
```

## Testing Configuration

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific markers
pytest -m unit
pytest -m "not slow"

# Run in parallel
pytest -n auto

# Run with verbose output
pytest -vv
```

### Pytest is configured in pyproject.toml

Key settings:
- Minimum version: pytest>=7.4.0
- Coverage for: runtime, planner modules
- Async support: pytest-asyncio
- Reports: terminal, HTML, XML

## Code Quality Tools

### Formatting

```bash
# Format code with black
black .

# Check formatting
black --check .
```

### Linting

```bash
# Lint with ruff (fast, modern)
ruff check .

# Fix auto-fixable issues
ruff check --fix .

# Traditional flake8
flake8 .
```

### Type Checking

```bash
# Type check with mypy
mypy runtime/ planner/
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run all hooks manually
pre-commit run --all-files

# Update hooks
pre-commit autoupdate
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        pip install -e ".[dev]"

    - name: Run tests
      run: |
        pytest --cov --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## Best Practices

### Adding New Dependencies

1. **Core dependency** - Add to `[project.dependencies]` in pyproject.toml
2. **Dev dependency** - Add to `[project.optional-dependencies.dev]`
3. **Update constraints** - Use `>=X.Y.Z,<X+1.0.0` format
4. **Test locally** - Install and run tests
5. **Update lock file** - If using pip-tools, run `pip-compile`

### Version Selection

- **Minimum version** - The lowest version you've tested
- **Maximum version** - Next major version (to prevent breaking changes)
- **Avoid exact pins** - Unless required for compatibility

### Security Updates

```bash
# Check for security vulnerabilities
pip-audit

# Update to latest secure versions
pip-compile --upgrade
```

## Troubleshooting

### Dependency Conflicts

```bash
# Show dependency tree
pip install pipdeptree
pipdeptree

# Check conflicts
pip check
```

### Clean Install

```bash
# Remove virtual environment
rm -rf venv/

# Create new environment
python3 -m venv venv
source venv/bin/activate

# Fresh install
pip install -e ".[dev]"
```

### Version Mismatch

If you encounter version conflicts:

1. Check `pip list` for installed versions
2. Verify pyproject.toml constraints
3. Update constraints if needed
4. Consider using pip-tools for resolution

## Migration from requirements.txt to pyproject.toml

Already complete! The project now uses:

- ✅ pyproject.toml as primary configuration
- ✅ Version constraints on all dependencies
- ✅ Separated optional dependencies
- ✅ Tool configurations in pyproject.toml
- ✅ Pre-commit hooks configured
- ✅ pytest properly configured with coverage

## References

- [PEP 621 - Storing project metadata in pyproject.toml](https://peps.python.org/pep-0621/)
- [pip-tools documentation](https://pip-tools.readthedocs.io/)
- [pytest documentation](https://docs.pytest.org/)
- [Python Packaging User Guide](https://packaging.python.org/)
