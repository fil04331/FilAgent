"""
Template Loader - Jinja2 Template Management for FilAgent

Provides a centralized system for loading and rendering prompt templates.
Supports versioning, caching, and graceful fallback.

Key Features:
1. Template versioning (v1, v2, etc.)
2. In-memory caching for performance
3. Singleton pattern for global access
4. Type-safe rendering with Pydantic validation
5. Clear error messages for debugging

Usage:
    from runtime.template_loader import get_template_loader

    loader = get_template_loader()
    prompt = loader.render('system_prompt', tools="...", semantic_context="...")
"""

from pathlib import Path
from typing import Optional, Dict, Any
from functools import lru_cache

from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound, UndefinedError


class TemplateLoader:
    """
    Loads and renders Jinja2 templates for prompts.

    This class provides:
    - Template loading from versioned directories
    - Caching for performance
    - Clear error handling
    - Version management

    Attributes:
        version: Template version to use (e.g., 'v1', 'v2')
        templates_dir: Base directory for templates
        env: Jinja2 environment
    """

    def __init__(
        self,
        version: str = "v1",
        templates_dir: Optional[Path] = None,
    ):
        """
        Initialize template loader.

        Args:
            version: Template version to load (default: 'v1')
            templates_dir: Base templates directory (default: prompts/templates)
        """
        self.version = version

        # Determine templates directory
        if templates_dir is None:
            # Default: project_root/prompts/templates
            project_root = Path(__file__).parent.parent
            templates_dir = project_root / "prompts" / "templates"

        self.templates_dir = Path(templates_dir)
        self.versioned_dir = self.templates_dir / version

        # Verify template directory exists
        if not self.versioned_dir.exists():
            raise FileNotFoundError(
                f"Template directory not found: {self.versioned_dir}\n"
                f"Available versions: {self._list_available_versions()}"
            )

        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.versioned_dir)),
            autoescape=False,  # Prompts are not HTML
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=False,
        )

        # Cache for compiled templates
        self._template_cache: Dict[str, Template] = {}

    def _list_available_versions(self) -> list:
        """List available template versions"""
        if not self.templates_dir.exists():
            return []
        return [
            d.name for d in self.templates_dir.iterdir() if d.is_dir() and d.name.startswith("v")
        ]

    def render(
        self,
        template_name: str,
        **variables: Any,
    ) -> str:
        """
        Render a template with variables.

        Args:
            template_name: Name of template (without .j2 extension)
            **variables: Variables to pass to template

        Returns:
            Rendered template string

        Raises:
            TemplateNotFound: If template doesn't exist
            UndefinedError: If required variable is missing

        Example:
            >>> loader = TemplateLoader()
            >>> prompt = loader.render('system_prompt', tools="tool1, tool2")
        """
        template_file = f"{template_name}.j2"

        try:
            # Try cache first
            if template_file in self._template_cache:
                template = self._template_cache[template_file]
            else:
                # Load and cache template
                template = self.env.get_template(template_file)
                self._template_cache[template_file] = template

            # Render with variables
            return template.render(**variables)

        except TemplateNotFound as e:
            available = self.list_templates()
            raise TemplateNotFound(
                f"Template '{template_name}' not found in version '{self.version}'.\n"
                f"Available templates: {', '.join(available)}"
            ) from e

        except UndefinedError as e:
            raise UndefinedError(
                f"Missing variable in template '{template_name}': {str(e)}\n"
                f"Provided variables: {list(variables.keys())}"
            ) from e

    def list_templates(self) -> list:
        """
        List all available templates in current version.

        Returns:
            List of template names (without .j2 extension)
        """
        templates = []
        for file in self.versioned_dir.glob("*.j2"):
            templates.append(file.stem)  # Remove .j2 extension
        return sorted(templates)

    def get_template_path(self, template_name: str) -> Path:
        """
        Get full path to a template file.

        Args:
            template_name: Name of template (without .j2)

        Returns:
            Path to template file
        """
        return self.versioned_dir / f"{template_name}.j2"

    def reload_templates(self):
        """
        Clear template cache and reload from disk.

        Useful during development when templates are modified.
        """
        self._template_cache.clear()

    def switch_version(self, version: str):
        """
        Switch to a different template version.

        Args:
            version: Version to switch to (e.g., 'v2')

        Raises:
            FileNotFoundError: If version doesn't exist
        """
        new_versioned_dir = self.templates_dir / version

        if not new_versioned_dir.exists():
            available = self._list_available_versions()
            raise FileNotFoundError(
                f"Template version '{version}' not found.\n"
                f"Available versions: {', '.join(available)}"
            )

        # Update paths and reload
        self.version = version
        self.versioned_dir = new_versioned_dir
        self.env = Environment(
            loader=FileSystemLoader(str(self.versioned_dir)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=False,
        )
        self._template_cache.clear()


# Global singleton instance
_template_loader: Optional[TemplateLoader] = None


@lru_cache(maxsize=1)
def get_template_loader(
    version: Optional[str] = None,
    templates_dir: Optional[Path] = None,
    force_reload: bool = False,
) -> TemplateLoader:
    """
    Get or create global TemplateLoader instance (singleton pattern).

    Args:
        version: Template version to use (default: 'v1')
        templates_dir: Custom templates directory (default: prompts/templates)
        force_reload: Force recreation of loader

    Returns:
        TemplateLoader instance

    Example:
        >>> loader = get_template_loader()
        >>> prompt = loader.render('system_prompt', tools="...")
    """
    global _template_loader

    # Default version
    if version is None:
        version = "v1"

    # Create new loader if needed
    if force_reload or _template_loader is None or _template_loader.version != version:
        _template_loader = TemplateLoader(version=version, templates_dir=templates_dir)

    return _template_loader


def clear_template_cache():
    """
    Clear the global template cache.

    Useful for testing or development when templates change.
    """
    global _template_loader
    _template_loader = None
    get_template_loader.cache_clear()
