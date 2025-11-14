# FilAgent - Dependency Management with PDM

## Table of Contents

1. [Overview](#overview)
2. [Why PDM?](#why-pdm)
3. [Installation](#installation)
4. [Daily Workflows](#daily-workflows)
5. [Project Configuration](#project-configuration)
6. [CI/CD Integration](#cicd-integration)
7. [Troubleshooting](#troubleshooting)
8. [Migration Guide](#migration-guide)
9. [Best Practices](#best-practices)
10. [Reference](#reference)

---

## Overview

FilAgent uses **PDM (Python Dependency Manager)** for modern, standards-based dependency management. PDM follows PEP 517, PEP 621, and other Python packaging standards, providing reproducible builds and efficient dependency resolution.

### Key Benefits

- ✅ **Standards-based**: Full PEP 517/621 compliance
- ✅ **Fast**: Parallel downloads and smart caching
- ✅ **Reproducible**: Lock files ensure consistent environments
- ✅ **Cross-platform**: Works on Linux, macOS, and Windows
- ✅ **Python version management**: Automatic Python version handling
- ✅ **No virtualenv overhead**: Uses PEP 582 `__pypackages__` by default

---

## Why PDM?

We chose PDM over other tools for several reasons:

| Feature | PDM | pip+venv | Poetry | pipenv |
|---------|-----|----------|--------|--------|
| PEP 621 compliance | ✅ | ❌ | ❌ | ❌ |
| Lock file | ✅ | ❌ | ✅ | ✅ |
| Parallel installation | ✅ | ❌ | ✅ | ❌ |
| Python management | ✅ | ❌ | ❌ | ✅ |
| Standard pyproject.toml | ✅ | ⚠️ | ⚠️ | ❌ |
| Performance | Excellent | Good | Good | Poor |

### PDM vs Poetry

While Poetry is popular, PDM offers:
- Better standards compliance (uses standard `[project]` table in pyproject.toml)
- Faster dependency resolution
- Better support for local dependencies
- Simpler, more predictable behavior

---

## Installation

### Prerequisites

- Python 3.10+ (we standardize on 3.12 for the project)
- pip (for installing pipx)

### Install PDM

#### Recommended: Via pipx (isolated installation)

```bash
# Install pipx if not already installed
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Install PDM
pipx install pdm

# Verify installation
pdm --version
```

#### Alternative: Direct pip install

```bash
pip install --user pdm
```

### Configure PDM for FilAgent

```bash
# Clone the repository
git clone https://github.com/fil04331/FilAgent.git
cd FilAgent

# Run the migration script
./scripts/migrate_to_pdm.sh

# Or manually:
pdm install  # Installs all dependencies
```

---

## Daily Workflows

### Basic Commands

#### Install dependencies

```bash
# Install production dependencies
pdm install --prod

# Install all dependencies (including dev)
pdm install

# Install with optional features
pdm install --with ml  # Install with ML dependencies
```

#### Add a new dependency

```bash
# Add to production dependencies
pdm add requests

# Add with version constraint
pdm add "pandas>=2.0"

# Add to dev dependencies
pdm add --dev pytest

# Add to optional group
pdm add --group ml torch
```

#### Update dependencies

```bash
# Update all dependencies
pdm update

# Update specific package
pdm update pandas

# Check for outdated packages
pdm list --outdated

# Update with safety checks
./scripts/update_dependencies.sh
```

#### Remove a dependency

```bash
# Remove from production
pdm remove requests

# Remove from dev
pdm remove --dev pytest
```

#### Run commands in PDM environment

```bash
# Run Python
pdm run python script.py

# Run tests
pdm run pytest

# Run the server
pdm run python runtime/server.py

# Or use the shortcut defined in pyproject.toml
pdm run server
```

### Working with Virtual Environments

PDM can use both `__pypackages__` (PEP 582) and traditional virtual environments:

```bash
# Activate the virtual environment
eval $(pdm venv activate)

# Or use pdm run prefix for all commands
pdm run <command>

# Deactivate
deactivate
```

### Lock File Management

```bash
# Generate/update lock file
pdm lock

# Check if lock file is up-to-date
pdm lock --check

# Install from lock file (CI/CD)
pdm install --no-lock
```

### Export Requirements

For backward compatibility:

```bash
# Export production dependencies only
pdm export -f requirements --without-hashes --prod -o requirements.txt

# Export production + dev dependencies
pdm export -f requirements --without-hashes --dev -o requirements-dev.txt

# Export production + ML dependencies
pdm export -f requirements --without-hashes --with ml -o requirements-ml.txt
```

---

## Project Configuration

### pyproject.toml Structure

```toml
[project]
name = "filagent"
version = "2.0.0"
description = "LLM Agent with Governance"
requires-python = ">=3.10,<3.15"

dependencies = [
    "fastapi>=0.104.0,<0.111",
    "pandas>=2.3.3,<3",
    "pyarrow>=17.0.0",  # Python 3.14 compatible
    # ... other dependencies
]

[project.optional-dependencies]
ml = ["llama-cpp-python>=0.2.0,<0.3"]
dev = ["pytest>=7.4.0,<9", "black>=23.11.0,<25"]

[tool.pdm]
distribution = false  # Don't build distributions

[tool.pdm.scripts]
# Custom commands
server = "python runtime/server.py"
test = "pytest"
format = "black ."
lint = "flake8 ."
```

### Python Version Management

The `.pdm-python` file locks the Python version:

```
3.12
```

To change Python version:

```bash
pdm use 3.12  # or another version
```

---

## CI/CD Integration

### GitHub Actions

Our workflows are configured to use PDM:

```yaml
- name: Set up PDM
  uses: pdm-project/setup-pdm@v4
  with:
    python-version: '3.12'
    cache: true

- name: Install dependencies
  run: |
    pdm install --no-lock  # Installs all dependencies from lock file

- name: Run tests
  run: pdm run pytest
```

### Caching

PDM provides excellent caching:

```yaml
- name: Cache PDM packages
  uses: actions/cache@v4
  with:
    path: |
      __pypackages__
      .pdm-build
    key: ${{ runner.os }}-pdm-${{ hashFiles('pdm.lock') }}
```

---

## Troubleshooting

### Common Issues

#### 1. "PDM not found"

```bash
# Ensure PDM is in PATH
export PATH="$HOME/.local/bin:$PATH"

# Or reinstall with pipx
pipx reinstall pdm
```

#### 2. "No Python interpreter found"

```bash
# Specify Python version explicitly
pdm use 3.12

# Or point to specific Python
pdm use /usr/bin/python3.12
```

#### 3. "Lock file out of date"

```bash
# Regenerate lock file
pdm lock

# Force update
pdm lock --refresh
```

#### 4. "Package conflicts"

```bash
# Check dependency tree
pdm list --tree

# Resolve conflicts
pdm update --update-eager
```

#### 5. PyArrow on Python 3.14

If you encounter PyArrow build issues with Python 3.14:

```bash
# Use Python 3.12 (recommended)
pdm use 3.12
pdm install

# Or install without PyArrow
pdm install --without pyarrow
```

### Debug Commands

```bash
# Show PDM configuration
pdm config

# Show Python info
pdm info

# Show environment info
pdm info --env

# Verbose output
pdm -v install
```

---

## Migration Guide

### From pip/requirements.txt

1. **Run migration script**:
   ```bash
   ./scripts/migrate_to_pdm.sh
   ```

2. **Manual migration**:
   ```bash
   # Install PDM
   pipx install pdm

   # Initialize PDM in project
   pdm init

   # Import from requirements.txt
   pdm import requirements.txt

   # Install dependencies
   pdm install
   ```

### From Poetry

1. **Export from Poetry**:
   ```bash
   poetry export -f requirements -o requirements.txt
   ```

2. **Import to PDM**:
   ```bash
   pdm import requirements.txt
   ```

3. **Adjust pyproject.toml**:
   - Move `[tool.poetry]` to `[project]`
   - Adjust dependency specifications

### From Pipenv

1. **Export from Pipenv**:
   ```bash
   pipenv requirements > requirements.txt
   ```

2. **Import to PDM**:
   ```bash
   pdm import requirements.txt
   ```

---

## Best Practices

### 1. Always Commit Lock Files

```bash
# Always commit these files
git add pdm.lock pyproject.toml
git commit -m "chore: Update dependencies"
```

### 2. Regular Updates

```bash
# Weekly security updates
./scripts/update_dependencies.sh --security-only

# Monthly full updates
./scripts/update_dependencies.sh
```

### 3. Use Groups for Optional Dependencies

```toml
[project.optional-dependencies]
ml = ["torch", "tensorflow"]
test = ["pytest", "pytest-cov"]
docs = ["mkdocs", "mkdocs-material"]
```

### 4. Pin Critical Dependencies

```toml
dependencies = [
    "pydantic==2.12.4",  # Exact version for critical packages
    "fastapi>=0.104.0,<0.111",  # Range for flexibility
]
```

### 5. Use Scripts for Common Tasks

```toml
[tool.pdm.scripts]
test = "pytest"
test-cov = "pytest --cov"
format = "black ."
lint = "flake8 ."
check = {composite = ["format", "lint", "test"]}
```

---

## Reference

### PDM Commands Cheat Sheet

| Command | Description |
|---------|-------------|
| `pdm install` | Install all dependencies |
| `pdm add <package>` | Add a dependency |
| `pdm remove <package>` | Remove a dependency |
| `pdm update` | Update all dependencies |
| `pdm list` | List installed packages |
| `pdm list --tree` | Show dependency tree |
| `pdm list --outdated` | Show outdated packages |
| `pdm run <command>` | Run command in PDM environment |
| `pdm lock` | Generate/update lock file |
| `pdm export` | Export to requirements.txt |
| `pdm info` | Show project information |
| `pdm config` | Show/edit configuration |

### Environment Variables

```bash
# PDM Configuration
export PDM_PYTHON=/usr/bin/python3.12  # Force Python version
export PDM_IGNORE_SAVED_PYTHON=1       # Ignore .pdm-python
export PDM_USE_VENV=1                  # Use virtual environment

# Project-specific
export FILAGENT_ENV=development        # FilAgent environment
```

### File Reference

| File | Purpose |
|------|---------|
| `pyproject.toml` | Project configuration and dependencies |
| `pdm.lock` | Locked dependency versions |
| `.pdm-python` | Python interpreter path |
| `.pdm.toml` | Local PDM configuration (git-ignored) |
| `__pypackages__/` | PEP 582 package directory |
| `.venv/` | Virtual environment (if using venv) |

### Useful Links

- [PDM Documentation](https://pdm-project.org/)
- [PEP 621 - Project Metadata](https://www.python.org/dev/peps/pep-0621/)
- [PEP 517 - Build Backend](https://www.python.org/dev/peps/pep-0517/)
- [PDM GitHub](https://github.com/pdm-project/pdm)
- [FilAgent Repository](https://github.com/fil04331/FilAgent)

---

## Support

For issues specific to FilAgent's PDM setup:

1. Check this documentation
2. Run diagnostic: `pdm info --env`
3. Check GitHub issues: https://github.com/fil04331/FilAgent/issues
4. Contact the team

For PDM-specific issues:

1. PDM Documentation: https://pdm-project.org/
2. PDM GitHub Issues: https://github.com/pdm-project/pdm/issues

---

*Last updated: November 2024*
*Version: 1.0.0*
*Maintainer: FilAgent Team*