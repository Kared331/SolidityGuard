from __future__ import annotations

from .template_loader import template_loader, PromptTemplate


class PromptRegistry:
    """Prompt registry: load templates by name with optional version pinning."""

    def get(self, name: str, version: str | None = None) -> PromptTemplate:
        template = template_loader.load(name)
        if version and template.version != version:
            raise ValueError(
                f"Template '{name}' version mismatch: "
                f"requested {version}, found {template.version}"
            )
        return template

    def render(self, name: str, **variables) -> tuple[str, str]:
        """Convenience: load and render in one call."""
        template = self.get(name)
        return template.render(**variables)

    def list_templates(self) -> list[str]:
        return template_loader.list_templates()


prompt_registry = PromptRegistry()
