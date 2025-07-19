import os
from typing import Dict
from jinja2 import Environment, FileSystemLoader, select_autoescape
from .template_utils import to_snake_case, to_pascal_case, singularize, pluralize
from . import template_utils


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
        self.env.filters["snake_case"] = to_snake_case
        self.env.filters["pascal_case"] = to_pascal_case
        self.env.filters["singularize"] = singularize
        self.env.filters["pluralize"] = pluralize

    def render_template(
        self,
        template_name: str,
        context: Dict,
        output_file: str,
        force_overwrite: bool = False,
    ) -> None:
        # Generate Model
        context["utils"] = template_utils
        if not os.path.exists(output_file) or force_overwrite is True:
            model_template = self.env.get_template(template_name)
            model_content = model_template.render(context)
            with open(output_file, "w") as f:
                f.write(model_content)
