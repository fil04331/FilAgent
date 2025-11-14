# PDM Quick Reference - FilAgent

## Installation & Setup

```bash
# Install PDM
pipx install pdm

# Clone and setup FilAgent
git clone https://github.com/fil04331/FilAgent.git
cd FilAgent
pdm install
```

## Essential Commands

### 📦 Dependency Management

```bash
pdm add <package>              # Add production dependency
pdm add --dev <package>        # Add dev dependency
pdm add --group ml <package>   # Add to optional group
pdm remove <package>           # Remove dependency
pdm update                     # Update all dependencies
pdm update <package>          # Update specific package
pdm list --outdated           # Check outdated packages
```

### 🚀 Running Code

```bash
pdm run python script.py      # Run Python script
pdm run pytest               # Run tests
pdm run server              # Start FilAgent server
eval $(pdm venv activate)   # Activate virtual environment
```

### 🔒 Lock File Operations

```bash
pdm lock                     # Generate/update lock file
pdm lock --check            # Verify lock file is current
pdm install --no-lock       # Install from existing lock
```

### 📋 Information & Export

```bash
pdm list                    # List installed packages
pdm list --tree            # Show dependency tree
pdm info                   # Show project info
pdm info --env             # Show environment info
pdm export -o requirements.txt  # Export to requirements
```

## Shortcuts (Defined in pyproject.toml)

```bash
pdm run test               # Run all tests
pdm run test-cov          # Run tests with coverage
pdm run format            # Format code with black
pdm run lint              # Lint with flake8
pdm run check             # Format + Lint + Test
pdm run server            # Start FilAgent server
pdm run security          # Run security scan
```

## Common Workflows

### 🆕 Add New Feature

```bash
pdm add <new-library>        # Add dependency
pdm run test                 # Test changes
pdm lock                     # Update lock file
git add pdm.lock pyproject.toml
git commit -m "feat: Add <feature>"
```

### 🔄 Update Dependencies

```bash
pdm list --outdated          # Check what needs updating
pdm update                   # Update all
pdm run test                # Verify tests pass
git add pdm.lock
git commit -m "chore: Update dependencies"
```

### 🐛 Debug Issues

```bash
pdm info --env              # Check environment
pdm list --tree             # Check dependency tree
pdm install --no-lock       # Reinstall from lock
pdm lock --refresh          # Force refresh lock file
```

### 🚢 Deploy

```bash
pdm install --prod --no-lock  # Install production only
pdm run server               # Start server
```

## Python Version

```bash
pdm use 3.12                # Switch to Python 3.12
cat .pdm-python            # Check current Python
```

## Environment Variables

```bash
PDM_PYTHON=/usr/bin/python3.12  # Force Python path
PDM_IGNORE_SAVED_PYTHON=1       # Ignore .pdm-python
```

## Files

- `pyproject.toml` - Project config & dependencies
- `pdm.lock` - Locked versions (commit this!)
- `.pdm-python` - Python version (commit this!)
- `__pypackages__/` - Installed packages (ignore)
- `.venv/` - Virtual environment (ignore)

## Troubleshooting

```bash
# PDM not found
export PATH="$HOME/.local/bin:$PATH"

# Lock file issues
pdm lock --refresh

# Clean reinstall
rm -rf __pypackages__ .venv
pdm install

# Check conflicts
pdm list --tree | grep <package>
```

## Help

```bash
pdm --help              # General help
pdm add --help         # Command-specific help
pdm config             # View configuration
```

---
**FilAgent Specific**: `./scripts/migrate_to_pdm.sh` - Full migration
**Updates**: `./scripts/update_dependencies.sh` - Safe updates with checks