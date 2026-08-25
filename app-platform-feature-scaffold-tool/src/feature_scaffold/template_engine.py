from __future__ import annotations

from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined


class TemplateEngine:
    def __init__(self, templates_dir: Path) -> None:
        self.environment = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
            variable_start_string="[[",
            variable_end_string="]]",
            comment_start_string="[#",
            comment_end_string="#]",
        )

    def render(self, template_path: str, context: dict) -> str:
        return self.environment.get_template(template_path).render(**context)