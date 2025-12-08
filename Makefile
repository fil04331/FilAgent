.PHONY: help install install-dev install-ml sync lock update export-requirements clean test lint format

# Display help
help:
	@echo "FilAgent - Dependency Management Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  make install             - Install production dependencies"
	@echo "  make install-dev         - Install all dependencies (including dev)"
	@echo "  make install-ml          - Install with ML dependencies"
	@echo "  make sync                - Sync dependencies from lock file"
	@echo "  make lock                - Update pdm.lock"
	@echo "  make update              - Update all dependencies"
	@echo "  make export-requirements - Regenerate all requirements*.txt files"
	@echo "  make clean               - Remove generated files and caches"
	@echo "  make test                - Run tests"
	@echo "  make lint                - Run linter"
	@echo "  make format              - Format code"
	@echo ""

# Install production dependencies only
install:
	pdm install --prod

# Install all dependencies (including dev)
install-dev:
	pdm install

# Install with ML dependencies
install-ml:
	pdm install -G ml

# Sync dependencies from lock file (for CI)
sync:
	pdm sync

# Update lock file
lock:
	pdm lock

# Update all dependencies
update:
	pdm update
	@$(MAKE) export-requirements

# Regenerate all requirements*.txt files from PDM lock
export-requirements:
	@echo "Regenerating requirements*.txt files..."
	pdm export --prod -o requirements.txt --without-hashes
	pdm export --prod -G dev -o requirements-dev.txt --without-hashes
	pdm export --prod -G ml -o requirements-ml.txt --without-hashes
	pdm export --prod -G dev -G ml -G ui -G benchmark -o requirements_complete.txt --without-hashes
	@echo "✓ All requirements files regenerated"

# Clean generated files and caches
clean:
	rm -rf __pypackages__
	rm -rf .venv
	rm -rf .pdm-build
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf htmlcov
	rm -rf dist
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# Run tests
test:
	pdm run pytest

# Run linter
lint:
	pdm run flake8 .

# Format code
format:
	pdm run black .
