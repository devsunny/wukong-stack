import os
from typing import Dict
from jinja2 import Environment, FileSystemLoader, select_autoescape
import re


class Jinja2TemplateRender:
    """
    Generates complete FastAPI backend with:
    - SQLAlchemy 2.0 ORM models
    - Pydantic v2 schemas
    - RESTful CRUD endpoints
    - Database-agnostic support
    - Pytest unit tests
    """

    def __init__(self, template_dir: str):
        """
        Args:
            tables: List of Table objects to generate
            db_type: Database dialect (postgresql, mysql, sqlite, oracle, mssql)
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(current_dir, template_dir)
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._add_jinja_filters()

    def _add_jinja_filters(self):
        """Adds custom filters to the Jinja2 environment."""
        self.env.filters["snake_case"] = self._to_snake_case
        self.env.filters["pascal_case"] = self._to_pascal_case
        self.env.filters["singularize"] = self._singularize
        self.env.filters["pluralize"] = self._pluralize

    def _to_snake_case(self, name: str) -> str:
        """Converts PascalCase/CamelCase/Space-separated to snake_case."""
        # Replace spaces with underscores first
        name = name.replace(" ", "_")
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    def _to_pascal_case(self, name: str) -> str:
        """Converts snake_case/kebab-case/space-separated to PascalCase."""
        return "".join(word.capitalize() for word in re.split(r"[-_ ]", name))

    def _singularize(self, name: str) -> str:
        """Basic singularization (for schema names)."""
        if name.endswith("s") and not name.endswith(
            "ss"
        ):  # Simple rule, can be improved
            return name[:-1]
        return name

    def _pluralize(self, name: str) -> str:
        """Basic pluralization (for router paths)."""
        if not name.endswith("s"):  # Simple rule, can be improved
            return name + "s"
        return name

    def render_template(
        self,
        template_name: str,
        context: Dict,
        output_file: str,
        force_overwrite: bool = False,
    ) -> None:
        # Generate Model

        if not os.path.exists(output_file) or force_overwrite is True:
            model_template = self.env.get_template(template_name)
            model_content = model_template.render(context)
            with open(output_file, "w") as f:
                f.write(model_content)
