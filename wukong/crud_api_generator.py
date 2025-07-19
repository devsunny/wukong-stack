import os
from typing import List, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
import re
from pgsql_parser import Table
from .template_utils import (
    to_pascal_case,
    to_snake_case,
    get_datetime_imports,
    get_pydantic_type,
    get_python_type,
    singularize,
    pluralize,
    get_pk_columns,
    is_auto_generated_pk,
)
from . import template_utils


class CRUDApiGenerator:
    """
    Generates complete FastAPI backend with:
    - SQLAlchemy 2.0 ORM models
    - Pydantic v2 schemas
    - RESTful CRUD endpoints
    - Database-agnostic support
    - Pytest unit tests
    - Dockerfile for the backend
    - Supports one-to-many relationships for specified root tables.
    """

    def __init__(
        self,
        tables: List[Table],
        db_type: str = "postgresql",
        root_table_names: Optional[List[str]] = None,
        root_module_name: Optional[str] = None,
    ):
        """
        Args:
            tables: List of Table objects to generate
            db_type: Database dialect (postgresql, mysql, sqlite, oracle, mssql)
            root_table_names: A list of table names that should be treated as "root"
                              tables, meaning their GET endpoints will eager-load
                              direct one-to-many relationships.
        """
        self.tables = tables
        self.db_type = db_type
        self.root_table_names = root_table_names if root_table_names is not None else []
        self.root_module_name = root_module_name
        # Set up Jinja2 environment
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(current_dir, "templates", "backend")
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._add_jinja_globals()  # Renamed to reflect purpose

    def _add_jinja_globals(self):
        """Adds custom filters and globals to the Jinja2 environment."""
        # Filters (methods that take an input and transform it)
        self.env.filters["snake_case"] = to_snake_case
        self.env.filters["pascal_case"] = to_pascal_case
        self.env.filters["singularize"] = singularize
        self.env.filters["pluralize"] = pluralize
        self.env.filters["get_datatime_imports"] = get_datetime_imports
        self.env.filters["get_pydantic_type"] = get_pydantic_type
        self.env.filters["get_python_type"] = get_python_type
        self.env.filters["is_auto_generated_pk"] = is_auto_generated_pk
        self.env.filters["get_pk_columns"] = get_pk_columns

    def generate_init(self, folder):
        with open(
            os.path.join(folder, "__init__.py"), mode="wt", encoding="utf-8"
        ) as fout:
            fout.write("# MODULE")

    def generate(self, output_dir: str = "backend", force_overwrite: bool = False):
        """
        Generates complete backend structure.

        Args:
            output_dir: The base directory for the generated backend files.
            force_overwrite: If True, overwrite existing files without prompt.
                             If False, skip existing files.
        """
        # Create output directories
        base_path = os.path.join(os.getcwd(), output_dir)
        os.makedirs(base_path, exist_ok=True)
        os.makedirs(os.path.join(base_path, "models"), exist_ok=True)
        self.generate_init(os.path.join(base_path, "models"))
        os.makedirs(os.path.join(base_path, "schemas"), exist_ok=True)
        self.generate_init(os.path.join(base_path, "schemas"))
        os.makedirs(os.path.join(base_path, "crud"), exist_ok=True)
        self.generate_init(os.path.join(base_path, "crud"))
        os.makedirs(os.path.join(base_path, "routers"), exist_ok=True)
        self.generate_init(os.path.join(base_path, "routers"))
        os.makedirs(
            os.path.join(base_path, "tests"), exist_ok=True
        )  # Create tests directory

        # Helper to write files with overwrite control
        def write_file(path, content, overwrite_always=False):
            # if os.path.exists(path) and not (force_overwrite or overwrite_always):
            #     print(f"Skipping existing file: {path}")
            #     return
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            print(f"Generated: {path}")

        # Generate per-table files
        for table in self.tables:
            table_snake_case = to_snake_case(singularize(table.name))
            table_pascal_case = to_pascal_case(singularize(table.name))

            # Prepare context for templates
            pk_columns = template_utils.get_pk_columns(table)
            context = {
                "table": table,
                "table_snake_case": table_snake_case,
                "table_pascal_case": table_pascal_case,
                "db_type": self.db_type,
                "columns": list(table.columns.values()),
                "utils": template_utils,
                "pk_columns": pk_columns,
                "is_composite_pk": len(pk_columns) > 1,  # New flag
                "is_root_table": table.name in self.root_table_names,
                "all_tables": self.tables,
                "child_tables": template_utils.get_child_tables(table, self.tables),
                "pk_name": pk_columns[0].name if pk_columns else None,
                "root_module_name": self.root_module_name,
            }

            # Generate Model
            model_template = self.env.get_template("model.py.j2")
            model_content = model_template.render(context)
            write_file(
                os.path.join(base_path, "models", f"{table_snake_case}.py"),
                model_content,
            )

            # Generate Schema
            schema_template = self.env.get_template("schema.py.j2")
            schema_content = schema_template.render(context)
            write_file(
                os.path.join(base_path, "schemas", f"{table_snake_case}.py"),
                schema_content,
            )

            # Generate CRUD
            crud_template = self.env.get_template("crud.py.j2")
            crud_content = crud_template.render(context)
            write_file(
                os.path.join(base_path, "crud", f"{table_snake_case}.py"), crud_content
            )

            # Generate Router (always overwrite)
            router_template = self.env.get_template("router.py.j2")
            router_content = router_template.render(context)
            write_file(
                os.path.join(base_path, "routers", f"{table_snake_case}.py"),
                router_content,
                overwrite_always=True,
            )

            # Generate Test
            test_router_template = self.env.get_template("test_router.py.j2")
            test_router_content = test_router_template.render(context)
            write_file(
                os.path.join(base_path, "tests", f"test_{table_snake_case}.py"),
                test_router_content,
            )

        import_prefix = "." if self.root_module_name else ""

        # Generate common files
        common_context = {
            "project_name": "CRUD FASTAPI",
            "tables": self.tables,
            "db_type": self.db_type,
            "router_imports": [
                f"from {import_prefix}routers.{to_snake_case(singularize(t.name))} import router as {to_snake_case(singularize(t.name))}_router"
                for t in self.tables
            ],
            "include_routers": [
                f"app.include_router({to_snake_case(singularize(t.name))}_router, prefix=f'/{pluralize(to_snake_case(singularize(t.name)))}', tags=['{pluralize(t.name)}'])"
                for t in self.tables
            ],
            "root_module_name": self.root_module_name,
        }

        # Database config
        database_template = self.env.get_template("database.py.j2")
        write_file(
            os.path.join(base_path, "database.py"),
            database_template.render(common_context),
        )

        # Config
        config_template = self.env.get_template("config.py.j2")
        write_file(
            os.path.join(base_path, "config.py"), config_template.render(common_context)
        )

        # Main app
        main_template = self.env.get_template("main.py.j2")
        write_file(
            os.path.join(base_path, "main.py"), main_template.render(common_context)
        )

        # Requirements
        requirements_template = self.env.get_template("requirements.txt.j2")
        write_file(
            os.path.join(base_path, "requirements.txt"),
            requirements_template.render(common_context),
        )

        # Dockerfile
        dockerfile_template = self.env.get_template("Dockerfile.j2")
        write_file(
            os.path.join(base_path, "Dockerfile"),
            dockerfile_template.render(common_context),
        )

        # Dockerfile
        dockerfile_template = self.env.get_template("readme.md.j2")
        write_file(
            os.path.join(base_path, "README.md"),
            dockerfile_template.render(common_context),
        )

        # .env.example
        env_example_template = self.env.get_template(".env.example.j2")
        write_file(
            os.path.join(base_path, ".env.example"),
            env_example_template.render(common_context),
        )

        # Dockerfile
        dockerfile_template = self.env.get_template("pytest.ini.j2")
        write_file(
            os.path.join(base_path, "pytest.ini"),
            dockerfile_template.render(common_context),
        )

        print(f"Backend API generated successfully in '{output_dir}' directory.")
