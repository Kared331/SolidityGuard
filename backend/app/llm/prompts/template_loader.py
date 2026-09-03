from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class PromptTemplate:
    name: str
    version: str
    description: str
    model_preference: list[str]
    temperature: float
    max_tokens: int
    system: str
    user: str

    def render(self, **variables) -> tuple[str, str]:
        """Render system and user prompts with variable substitution."""
        system = self.system.format(**variables) if variables else self.system
        user = self.user.format(**variables) if variables else self.user
        return system, user


class TemplateLoader:
    """Loads Prompt templates from YAML files."""

    def __init__(self, templates_dir: Path):
        self.templates_dir = Path(templates_dir)

    def load(self, name: str) -> PromptTemplate:
        filepath = self.templates_dir / f"{name}.yaml"
        if not filepath.exists():
            raise FileNotFoundError(f"Prompt template not found: {filepath}")
        with open(filepath, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return PromptTemplate(
            name=data["name"],
            version=data["version"],
            description=data.get("description", ""),
            model_preference=data.get("model_preference", []),
            temperature=data.get("temperature", 0.2),
            max_tokens=data.get("max_tokens", 4096),
            system=data["system"],
            user=data["user"],
        )

    def list_templates(self) -> list[str]:
        """List available template names (without .yaml extension)."""
        return [p.stem for p in self.templates_dir.glob("*.yaml")]


# Default loader pointing to the templates directory
_prompts_dir = Path(__file__).parent / "templates" / "audit"
template_loader = TemplateLoader(_prompts_dir)
