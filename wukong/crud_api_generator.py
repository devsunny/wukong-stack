import os
from typing import List, Optional, Tuple, Dict
from jinja2 import Environment, FileSystemLoader, select_autoescape
import re


# Import schema classes from the external pgsql_parser module
# These are assumed to be available or defined in a common utility file.
# For this example, we'll keep a minimal definition here for self-containment
# but in a larger project, these would be in a shared 'schema_definitions.py'
# from pgsql_parser import Table, Column, ForeignKey # Added as requested, commented out
class Column:
    def __init__(
        self,
        name: str,
        data_type: str,
        is_primary: bool = False,
        nullable: bool = True,
        char_length: Optional[int] = None,
        numeric_precision: Optional[int] = None,
        numeric_scale: Optional[int] = None,
        default_value: Optional[str] = None,
        foreign_key_ref: Optional[Tuple[str, str, str]] = None,
        constraints: Optional[List[Dict]] = None,
    ):
        self.name = name
        self.data_type = data_type
        self.is_primary = is_primary
        self.nullable = nullable
        self.char_length = char_length
        self.numeric_precision = numeric_precision
        self.numeric_scale = numeric_scale
        self.default_value = default_value
        self.foreign_key_ref = foreign_key_ref  # (schema, table, column)
        self.constraints = constraints if constraints is not None else []


class PrimaryKey:
    def __init__(self, name: str, columns: List[str]):
        self.name = name
        self.columns = columns


class ForeignKey:
    def __init__(
        self, name: str, columns: List[str], ref_table: str, ref_columns: List[str]
    ):
        self.name = name
        self.columns = columns
        self.ref_table = ref_table
        self.ref_columns = ref_columns


class Constraint:
    def __init__(self, name: str, type: str, columns: List[str]):
        self.name = name
        self.type = type
        self.columns = columns


class Index:
    def __init__(self, name: str, columns: List[str], unique: bool = False):
        self.name = name
        self.columns = columns
        self.unique = unique


class Table:
    def __init__(self, name: str, schema: Optional[str] = None):
        self.name = name
        self.schema = schema
        self.columns: Dict[str, Column] = {}
        self.primary_key: Optional[PrimaryKey] = None
        self.foreign_keys: List[ForeignKey] = []
        self.constraints: List[Constraint] = []
        self.indexes: List[Index] = []


# Define declarative_base here or import it from a common module if preferred
# from sqlalchemy.ext.declarative import declarative_base
# Base = declarative_base() # Removed as it's not directly used by the generator class


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
        self.env.filters["snake_case"] = self._to_snake_case
        self.env.filters["pascal_case"] = self._to_pascal_case
        self.env.filters["singularize"] = self._singularize
        self.env.filters["pluralize"] = self._pluralize

        # Globals (methods that can be called directly like functions in the template)
        # We're now passing the class itself and relying on explicit calls in templates
        self.env.globals["CRUDApiGenerator"] = CRUDApiGenerator
        self.env.globals["get_child_tables"] = (
            self._get_child_tables
        )  # This one still needs self.tables, so keep as instance method and pass directly

    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Converts PascalCase/CamelCase/Space-separated to snake_case."""
        # Replace spaces with underscores first
        name = name.replace(" ", "_")
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    @staticmethod
    def _to_pascal_case(name: str) -> str:
        """Converts snake_case/kebab-case/space-separated to PascalCase."""
        return "".join(word.capitalize() for word in re.split(r"[-_ ]", name))

    @staticmethod
    def _singularize(name: str) -> str:
        """Basic singularization (for schema names)."""
        if name.endswith("s") and not name.endswith(
            "ss"
        ):  # Simple rule, can be improved
            return name[:-1]
        return name

    @staticmethod
    def _pluralize(name: str) -> str:
        """Basic pluralization (for router paths)."""
        if not name.endswith("s"):  # Simple rule, can be improved
            return name + "s"
        return name

    @staticmethod
    def _sql_type_to_python_type(column: Column) -> str:
        """Converts SQL data types to Python types."""
        data_type = column.data_type.lower()
        if data_type in ["varchar", "text", "char", "uuid", "json", "jsonb"]:
            return "str"
        elif data_type in ["integer", "smallint", "bigint", "serial", "bigserial"]:
            return "int"
        elif data_type in ["boolean"]:
            return "bool"
        elif data_type in ["float", "double precision", "real", "numeric", "decimal"]:
            return "float"  # Or Decimal from decimal module
        elif data_type in ["date"]:
            return "date"
        elif data_type in ["timestamp", "timestamptz", "datetime"]:
            return "datetime"
        elif data_type in ["bytea", "blob"]:
            return "bytes"
        return "Any"  # Fallback for unhandled types

    @staticmethod
    def _get_pydantic_type(column: Column) -> str:
        """Returns the Pydantic type string (e.g., str, Optional[int])."""
        py_type = CRUDApiGenerator._sql_type_to_python_type(column)
        if py_type == "date":
            py_type = "date"  # pydantic.types.date
        elif py_type == "datetime":
            py_type = "datetime"  # datetime.datetime
        elif py_type == "Any":
            return "typing.Any"

        if column.nullable:
            return f"Optional[{py_type}]"
        return py_type

    @staticmethod
    def _get_sqlalchemy_type(column: Column) -> str:
        """Returns the SQLAlchemy type string (e.g., String, Integer)."""
        data_type = column.data_type.lower()
        if data_type in ["varchar", "char"]:
            return f"String({column.char_length})" if column.char_length else "String"
        elif data_type == "text":
            return "Text"
        elif data_type in ["integer", "smallint", "bigint", "serial", "bigserial"]:
            return "Integer"
        elif data_type == "boolean":
            return "Boolean"
        elif data_type in ["float", "real"]:
            return "Float"
        elif data_type in ["double precision"]:
            return "Double"
        elif data_type in ["numeric", "decimal"]:
            precision = (
                column.numeric_precision if column.numeric_precision is not None else ""
            )
            scale = (
                f", {column.numeric_scale}" if column.numeric_scale is not None else ""
            )
            return f"Numeric({precision}{scale})"
        elif data_type == "date":
            return "Date"
        elif data_type in ["timestamp", "timestamptz", "datetime"]:
            return "DateTime(timezone=True)" if "tz" in data_type else "DateTime"
        elif data_type == "uuid":
            return "UUID(as_uuid=True)"
        elif data_type in ["json", "jsonb"]:
            return "JSON"
        elif data_type in ["bytea", "blob"]:
            return "LargeBinary"
        return "String"  # Default fallback

    @staticmethod
    def _get_pk_column(table: Table) -> Optional[Column]:
        """Returns the primary key column, assuming a single PK column for simplicity."""
        if table.primary_key and table.primary_key.columns:
            pk_col_name = table.primary_key.columns[0]
            return table.columns.get(pk_col_name)
        return None

    @staticmethod
    def _get_pk_type(table: Table) -> str:
        """Returns the Python type of the primary key."""
        pk_column = CRUDApiGenerator._get_pk_column(table)
        if pk_column:
            return CRUDApiGenerator._sql_type_to_python_type(pk_column)
        return "int"  # Default to int if no PK found

    @staticmethod
    def _get_pk_name(table: Table) -> str:
        """Returns the name of the primary key column."""
        pk_column = CRUDApiGenerator._get_pk_column(table)
        if pk_column:
            return pk_column.name
        return "id"  # Default to 'id'

    @staticmethod
    def _get_pk_columns(table: Table) -> List[Column]:
        """Returns a list of primary key columns for a table."""
        if table.primary_key and table.primary_key.columns:
            return [
                table.columns[col_name]
                for col_name in table.primary_key.columns
                if col_name in table.columns
            ]
        return []

    @staticmethod
    def _get_pk_names_for_repr(table: Table) -> str:
        """Returns a string of primary key assignments for __repr__."""
        pk_cols = CRUDApiGenerator._get_pk_columns(table)
        if not pk_cols:
            return "id=None"  # Fallback if no PK

        repr_parts = []
        for col in pk_cols:
            repr_parts.append(
                f"{CRUDApiGenerator._to_snake_case(col.name)}={{self.{CRUDApiGenerator._to_snake_case(col.name)}}}"
            )
        return ", ".join(repr_parts)

    @staticmethod
    def _is_auto_generated_pk(column: Column) -> bool:
        """Checks if a column is a primary key and is likely auto-generated (serial, uuid)."""
        if not column.is_primary:
            return False
        data_type = column.data_type.lower()
        # Common auto-incrementing integer types
        if (
            data_type in ["serial", "bigserial", "integer", "smallint", "bigint"]
            and column.default_value is None
        ):
            return True
        # Common auto-generated UUID types (check for func.uuid_generate_v4() or similar in default_value)
        if data_type == "uuid" and (
            column.default_value is None
            or "uuid_generate" in str(column.default_value).lower()
        ):
            return True
        return False

    @staticmethod
    def _should_use_server_default(column: Column) -> bool:
        """Determines if a column should use server_default=func.now()."""
        # Check for specific SQL function strings in default_value
        if isinstance(column.default_value, str) and column.default_value.upper() in [
            "CURRENT_TIMESTAMP",
            "NOW()",
            "GETDATE()",
        ]:
            return True
        return False

    def _get_child_tables(self, parent_table: Table) -> List[Table]:
        """Returns a list of tables that have a foreign key referencing the parent_table."""
        children = []
        for table in self.tables:
            if table.name == parent_table.name:
                continue
            for fk in table.foreign_keys:
                if fk.ref_table == parent_table.name:
                    children.append(table)
                    break  # A table can only be a child once to a specific parent for simplicity
        return children

    @staticmethod
    def _has_datetime_or_date_column(table: Table) -> bool:
        """Checks if the table has any date or datetime columns."""
        for column in table.columns.values():
            if column.data_type.lower() in [
                "date",
                "timestamp",
                "timestamptz",
                "datetime",
            ]:
                return True
        return False

    @staticmethod
    def _get_default_value_for_type(column: Column):
        """Returns a suitable default value for testing based on column type."""
        data_type = column.data_type.lower()
        if data_type in ["varchar", "text", "char", "uuid", "json", "jsonb"]:
            return f"'{CRUDApiGenerator._to_snake_case(column.name)}_test'"
        elif data_type in ["integer", "smallint", "bigint", "serial", "bigserial"]:
            return 1
        elif data_type in ["boolean"]:
            return "True"
        elif data_type in ["float", "double precision", "real", "numeric", "decimal"]:
            return 1.0
        elif data_type in ["date"]:
            return "'2024-01-01'"
        elif data_type in ["timestamp", "timestamptz", "datetime"]:
            return "'2024-01-01T12:00:00Z'"
        elif data_type in ["bytea", "blob"]:
            return "'test_bytes'"
        return "'default_value'"

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
        os.makedirs(os.path.join(base_path, "schemas"), exist_ok=True)
        os.makedirs(os.path.join(base_path, "crud"), exist_ok=True)
        os.makedirs(os.path.join(base_path, "routers"), exist_ok=True)
        os.makedirs(
            os.path.join(base_path, "tests"), exist_ok=True
        )  # Create tests directory

        # Helper to write files with overwrite control
        def write_file(path, content, overwrite_always=False):
            if os.path.exists(path) and not (force_overwrite or overwrite_always):
                print(f"Skipping existing file: {path}")
                return
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            print(f"Generated: {path}")

        # Generate per-table files
        for table in self.tables:
            table_snake_case = self._to_snake_case(table.name)
            table_pascal_case = self._to_pascal_case(table.name)

            # Prepare context for templates
            context = {
                "table": table,
                "table_snake_case": table_snake_case,
                "table_pascal_case": table_pascal_case,
                "db_type": self.db_type,
                "columns": list(table.columns.values()),
                "pk_column": self._get_pk_column(table),
                "pk_type": self._get_pk_type(table),
                "pk_name": self._get_pk_name(table),
                "is_root_table": table.name in self.root_table_names,
                "all_tables": self.tables,  # Pass all tables to resolve relationships
                "child_tables": self._get_child_tables(
                    table
                ),  # Get direct children for this table
                "has_datetime_or_date_column": self._has_datetime_or_date_column(
                    table
                ),  # New flag for schema imports
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

        # Generate common files
        common_context = {
            "tables": self.tables,
            "db_type": self.db_type,
            "router_imports": [
                f"from .routers.{self._to_snake_case(t.name)} import router as {self._to_snake_case(t.name)}_router"
                for t in self.tables
            ],
            "include_routers": [
                f"app.include_router({self._to_snake_case(t.name)}_router, prefix=f'/{self._pluralize(self._to_snake_case(t.name))}', tags=['{self._pluralize(t.name)}'])"
                for t in self.tables
            ],
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

        # .env.example
        env_example_template = self.env.get_template(".env.example.j2")
        write_file(
            os.path.join(base_path, ".env.example"),
            env_example_template.render(common_context),
        )

        print(f"Backend API generated successfully in '{output_dir}' directory.")


# --- Placeholder Jinja2 Templates (These would typically be in templates/backend/) ---

# model.py.j2
MODEL_TEMPLATE = """
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Numeric, Date, UUID, LargeBinary, JSON, func, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import List
from datetime import datetime, date
import uuid

# Base is typically imported from database.py in a real project structure
# For standalone template rendering, we define it here.
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

# Import all other models for type hinting in relationships
{% for other_table in all_tables %}
{% if other_table.name != table.name %}
from .{{ other_table.name | snake_case }} import {{ other_table.name | pascal_case }}
{% endif %}
{% endfor %}

class {{ table_pascal_case }}(Base):
    __tablename__ = "{{ table_snake_case }}"
    {% if table.schema %}
    __table_args__ = ({'schema': '{{ table.schema }}'},)
    {% endif %}

    {% for column in columns %}
    {{ column.name | snake_case }}: Mapped[{{ CRUDApiGenerator._sql_type_to_python_type(column) }}] = mapped_column(
        {% if column.foreign_key_ref %}
        Column(
            {{ CRUDApiGenerator._get_sqlalchemy_type(column) }},
            ForeignKey("{{ column.foreign_key_ref[1] }}.{{ column.foreign_key_ref[2] }}"),
            {% if column.is_primary %}primary_key=True,{% endif %}
            {% if not column.nullable %}nullable=False,{% endif %}
            {% if column.default_value is not none %}{% if CRUDApiGenerator._should_use_server_default(column) %}server_default=func.now(),{% elif column.data_type.lower() in ['varchar', 'text', 'char', 'uuid', 'json', 'jsonb', 'date', 'timestamp', 'timestamptz', 'datetime', 'time'] %}default="{{ column.default_value }}",{% else %}default={{ column.default_value }},{% endif %}{% endif %}
        )
        {% else %}
        {{ CRUDApiGenerator._get_sqlalchemy_type(column) }},
        {% if column.is_primary %}
        primary_key=True,
        {% endif %}
        {% if not column.nullable %}
        nullable=False,
        {% endif %}
        {% if CRUDApiGenerator._should_use_server_default(column) %}
        server_default=func.now(),
        {% elif column.default_value is not none %} {# Only use default if not server_default and default_value exists #}
            {% if column.data_type.lower() in ['varchar', 'text', 'char', 'uuid', 'json', 'jsonb', 'date', 'timestamp', 'timestamptz', 'datetime', 'time'] %}
        default="{{ column.default_value }}",
            {% else %}
        default={{ column.default_value }},
            {% endif %}
        {% endif %}
        {% endif %}
    )
    {% endfor %}

    {% for fk in table.foreign_keys %}
    # Relationship from child (this table) to parent (referenced table)
    # E.g., if this is a 'Post' table with 'user_id' FK to 'User', this creates 'post.user_object'
    {{ fk.ref_table | singularize | snake_case }}_object: Mapped[{{ fk.ref_table | pascal_case }}] = relationship(
        foreign_keys=[{{ fk.columns | map('snake_case') | join(', ') }}],
        back_populates="{{ table_snake_case | pluralize }}_collection" # back_populates points to the collection on the parent
    )
    {% endfor %}

    {% for child_table in all_tables %}
    {% if child_table.name != table.name %}
        {% for fk in child_table.foreign_keys %}
            {% if fk.ref_table == table.name %}
    # Relationship from parent (this table) to child ({{ child_table.name }})
    # E.g., if this is a 'User' table, and 'Post' has 'user_id' FK to 'User', this creates 'user.posts_collection'
    {{ child_table.name | pluralize | snake_case }}_collection: Mapped[List[{{ child_table.name | pascal_case }}]] = relationship(
        back_populates="{{ child_table.name | singularize | snake_case }}_object" # back_populates points to the object on the child
    )
            {% endif %}
        {% endfor %}
    {% endif %}
    {% endfor %}

    def __repr__(self):
        return f"<{{ table_pascal_case }}({{ CRUDApiGenerator._get_pk_names_for_repr(table) }})>"
"""

# schema.py.j2
SCHEMA_TEMPLATE = """
from __future__ import annotations # For Pydantic v2 forward references
from pydantic import BaseModel, Field
from typing import Optional, List, Any

{% if CRUDApiGenerator._has_datetime_or_date_column(table) %}
from datetime import datetime, date
{% endif %}

{% for other_table in all_tables %}
{% if other_table.name != table.name %}
    {% for fk in other_table.foreign_keys %}
        {# Check if 'this' table is the referenced table (parent) for 'other_table' (child) #}
        {% if fk.ref_table == table.name %}
from .{{ other_table.name | snake_case }} import {{ other_table.name | pascal_case }}Read
        {% endif %}
    {% endfor %}
{% endif %}
{% endfor %}


# Base Schema
class {{ table_pascal_case }}Base(BaseModel):
    {% for column in columns %}
    {{ column.name | snake_case }}: {{ CRUDApiGenerator._get_pydantic_type(column) }}
    {% endfor %}

    class Config:
        from_attributes = True # For Pydantic v2
        populate_by_name = True # Allow field names to be populated by their alias (if any)


# Create Schema
class {{ table_pascal_case }}Create({{ table_pascal_case }}Base):
    {% for column in columns %}
    {% if CRUDApiGenerator._is_auto_generated_pk(column) %}
    {{ column.name | snake_case }}: Any = Field(default=None, exclude=True) # Exclude auto-generated PK from input
    {% endif %}
    {% endfor %}
    pass


# Update Schema
class {{ table_pascal_case }}Update({{ table_pascal_case }}Base):
    {% for column in columns %}
    {{ column.name | snake_case }}: Optional[{{ CRUDApiGenerator._get_pydantic_type(column) }}] = Field(default=None)
    {% endfor %}

# Read Schema (basic, without relations)
class {{ table_pascal_case }}Read({{ table_pascal_case }}Base):
    {{ CRUDApiGenerator._get_pk_name(table) | snake_case }}: {{ CRUDApiGenerator._get_pk_type(table) }}


# Final Response Schema (includes relationships if applicable)
class {{ table_pascal_case }}({{ table_pascal_case }}Read):
    {% for child_table in all_tables %}
    {% if child_table.name != table.name %}
        {% for fk in child_table.foreign_keys %}
            {% if fk.ref_table == table.name %}
    {{ child_table.name | pluralize | snake_case }}_collection: List[{{ child_table.name | pascal_case }}Read] = []
            {% endif %}
        {% endfor %}
    {% endif %}
    {% endfor %}
    pass # No new fields needed if only inheriting and adding relationships
"""


# crud.py.j2
CRUD_TEMPLATE = '''
from sqlalchemy.orm import Session, selectinload
from ..models.{{ table_snake_case }} import {{ table_pascal_case }}
from ..schemas.{{ table_snake_case }} import {{ table_pascal_case }}Create, {{ table_pascal_case }}Update, {{ table_pascal_case }}Read
from typing import List, Optional

def get_{{ table_snake_case }}(db: Session, {{ CRUDApiGenerator._get_pk_name(table) | snake_case }}: {{ CRUDApiGenerator._get_pk_type(table) }}, eager_load_relations: bool = False) -> Optional[{{ table_pascal_case }}]:
    """
    Retrieve a single {{ table_snake_case }} by its primary key.
    If eager_load_relations is True, direct one-to-many relationships are loaded.
    """
    query = db.query({{ table_pascal_case }})
    {% for child_table in all_tables %}
    {% if child_table.name != table.name %}
        {% for fk in child_table.foreign_keys %}
            {% if fk.ref_table == table.name %}
    if eager_load_relations:
        query = query.options(selectinload({{ table_pascal_case }}.{{ child_table.name | pluralize | snake_case }}_collection))
            {% endif %}
        {% endfor %}
    {% endif %}
    {% endfor %}
    return query.filter({{ table_pascal_case }}.{{ CRUDApiGenerator._get_pk_name(table) | snake_case }} == {{ CRUDApiGenerator._get_pk_name(table) | snake_case }}).first()

def get_all_{{ table_snake_case | pluralize }}(db: Session, skip: int = 0, limit: int = 100, eager_load_relations: bool = False) -> List[{{ table_pascal_case }}]:
    """
    Retrieve a list of all {{ table_snake_case | pluralize }}.
    If eager_load_relations is True, direct one-to-many relationships are loaded.
    """
    query = db.query({{ table_pascal_case }})
    {% for child_table in all_tables %}
    {% if child_table.name != table.name %}
        {% for fk in child_table.foreign_keys %}
            {% if fk.ref_table == table.name %}
    if eager_load_relations:
        query = query.options(selectinload({{ table_pascal_case }}.{{ child_table.name | pluralize | snake_case }}_collection))
            {% endif %}
        {% endfor %}
    {% endif %}
    {% endfor %}
    return query.offset(skip).limit(limit).all()

def create_{{ table_snake_case }}(db: Session, {{ table_snake_case }}: {{ table_pascal_case }}Create) -> {{ table_pascal_case }}Read:
    """
    Create a new {{ table_snake_case }} record.
    """
    db_{{ table_snake_case }} = {{ table_pascal_case }}(**{{ table_snake_case }}.model_dump())
    db.add(db_{{ table_snake_case }})
    db.commit()
    db.refresh(db_{{ table_snake_case }})
    return db_{{ table_snake_case }}

def update_{{ table_snake_case }}(db: Session, {{ CRUDApiGenerator._get_pk_name(table) | snake_case }}: {{ CRUDApiGenerator._get_pk_type(table) }}, {{ table_snake_case }}_update: {{ table_pascal_case }}Update) -> Optional[{{ table_pascal_case }}Read]:
    """
    Update an existing {{ table_snake_case }} record.
    """
    db_{{ table_snake_case }} = db.query({{ table_pascal_case }}).filter({{ table_pascal_case }}.{{ CRUDApiGenerator._get_pk_name(table) | snake_case }} == {{ CRUDApiGenerator._get_pk_name(table) | snake_case }}).first()
    if not db_{{ table_snake_case }}:
        return None
    
    for key, value in {{ table_snake_case }}_update.model_dump(exclude_unset=True).items():
        setattr(db_{{ table_snake_case }}, key, value)
    
    db.commit()
    db.refresh(db_{{ table_snake_case }})
    return db_{{ table_snake_case }}

def delete_{{ table_snake_case }}(db: Session, {{ CRUDApiGenerator._get_pk_name(table) | snake_case }}: {{ CRUDApiGenerator._get_pk_type(table) }}) -> Optional[{{ table_pascal_case }}Read]:
    """
    Delete a {{ table_snake_case }} record.
    """
    db_{{ table_snake_case }} = db.query({{ table_pascal_case }}).filter({{ table_pascal_case }}.{{ CRUDApiGenerator._get_pk_name(table) | snake_case }} == {{ CRUDApiGenerator._get_pk_name(table) | snake_case }}).first()
    if not db_{{ table_snake_case }}:
        return None
    db.delete(db_{{ table_snake_case }})
    db.commit()
    return db_{{ table_snake_case }}
'''

# router.py.j2
ROUTER_TEMPLATE = '''
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from .. import crud
from ..schemas.{{ table_snake_case }} import {{ table_pascal_case }}Create, {{ table_pascal_case }}Update, {{ table_pascal_case }}Read, {{ table_pascal_case }}
from ..database import get_db

router = APIRouter()

@router.post("/", response_model={{ table_pascal_case }}Read, status_code=status.HTTP_201_CREATED)
def create_new_{{ table_snake_case }}({{ table_snake_case }}: {{ table_pascal_case }}Create, db: Session = Depends(get_db)):
    """
    Create a new {{ table_snake_case }} record.
    """
    return crud.create_{{ table_snake_case }}(db=db, {{ table_snake_case }}={{ table_snake_case }})

@router.get("/", response_model=List[{{ table_pascal_case }}]) # Use the full schema for list
def read_all_{{ table_snake_case | pluralize }}(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    eager_load_relations: bool = False # Allow eager loading for all
):
    """
    Retrieve a list of all {{ table_snake_case | pluralize }}.
    """
    {{ table_snake_case | pluralize }} = crud.get_all_{{ table_snake_case | pluralize }}(db, skip=skip, limit=limit, eager_load_relations=eager_load_relations)
    return {{ table_snake_case | pluralize }}

@router.get("/{{ '{' }}{{ CRUDApiGenerator._get_pk_name(table) | snake_case }}{{ '}' }}", response_model={{ table_pascal_case }}) # Use the full schema for single item
def read_{{ table_snake_case }}(
    {{ CRUDApiGenerator._get_pk_name(table) | snake_case }}: {{ CRUDApiGenerator._get_pk_type(table) }}, 
    db: Session = Depends(get_db),
    eager_load_relations: bool = False # Allow eager loading for single
):
    """
    Retrieve a single {{ table_snake_case }} by its primary key.
    """
    db_{{ table_snake_case }} = crud.get_{{ table_snake_case }}(db, {{ CRUDApiGenerator._get_pk_name(table) | snake_case }}={{ CRUDApiGenerator._get_pk_name(table) | snake_case }}, eager_load_relations=eager_load_relations)
    if db_{{ table_snake_case }} is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="{{ table_pascal_case }} not found")
    return db_{{ table_snake_case }}

@router.put("/{{ '{' }}{{ CRUDApiGenerator._get_pk_name(table) | snake_case }}{{ '}' }}", response_model={{ table_pascal_case }}Read)
def update_existing_{{ table_snake_case }}({{ CRUDApiGenerator._get_pk_name(table) | snake_case }}: {{ CRUDApiGenerator._get_pk_type(table) }}, {{ table_snake_case }}_update: {{ table_pascal_case }}Update, db: Session = Depends(get_db)):
    """
    Update an existing {{ table_snake_case }} record.
    """
    db_{{ table_snake_case }} = crud.update_{{ table_snake_case }}(db, {{ CRUDApiGenerator._get_pk_name(table) | snake_case }}={{ CRUDApiGenerator._get_pk_name(table) | snake_case }}, {{ table_snake_case }}_update={{ table_snake_case }}_update)
    if db_{{ table_snake_case }} is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="{{ table_pascal_case }} not found")
    return db_{{ table_snake_case }}

@router.delete("/{{ '{' }}{{ CRUDApiGenerator._get_pk_name(table) | snake_case }}{{ '}' }}", response_model={{ table_pascal_case }}Read)
def delete_existing_{{ table_snake_case }}({{ CRUDApiGenerator._get_pk_name(table) | snake_case }}: {{ CRUDApiGenerator._get_pk_type(table) }}, db: Session = Depends(get_db)):
    """
    Delete a {{ table_snake_case }} record.
    """
    db_{{ table_snake_case }} = crud.delete_{{ table_snake_case }}(db, {{ CRUDApiGenerator._get_pk_name(table) | snake_case }}={{ CRUDApiGenerator._get_pk_name(table) | snake_case }})
    if db_{{ table_snake_case }} is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="{{ table_pascal_case }} not found")
    return db_{{ table_snake_case }}
'''

# database.py.j2
DATABASE_TEMPLATE = '''
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from .config import settings
import os

# Determine the database URL based on the selected db_type
{% if db_type == "sqlite" %}
SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
# For SQLite, connect_args are needed for proper multi-threading in FastAPI
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, echo=True
)
{% else %}
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=True)
{% endif %}

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_db_and_tables():
    """Creates all defined tables in the database."""
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    # This block is for local testing/setup
    # You might want to run this once to create your database tables
    print("Creating database tables...")
    create_db_and_tables()
    print("Tables created successfully.")
'''

# config.py.j2
CONFIG_TEMPLATE = """
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://user:password@localhost:5432/dbname"
    # Example for other DB types:
    # SQLITE: "sqlite:///./sql_app.db"
    # MYSQL: "mysql+mysqlconnector://user:3306/dbname"
    # MSSQL: "mssql+pyodbc://user:password@localhost:1433/dbname?driver=ODBC+Driver+17+for+SQL+Server"
    # ORACLE: "oracle+cx_oracle://user:password@localhost:1521/dbname"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
"""

# main.py.j2
MAIN_TEMPLATE = """
from fastapi import FastAPI
from .database import create_db_and_tables
{% for router_import in router_imports %}
{{ router_import }}
{% endfor %}

app = FastAPI(
    title="Generated CRUD API",
    description="Automatically generated FastAPI application with CRUD operations for your database tables.",
    version="1.0.0",
)

# Create database tables on startup
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

{% for include_router in include_routers %}
{{ include_router }}
{% endfor %}

@app.get("/")
def read_root():
    return {"message": "Welcome to the generated FastAPI CRUD API!"}
"""

# requirements.txt.j2
REQUIREMENTS_TEMPLATE = """
fastapi==0.111.0
uvicorn==0.30.1
sqlalchemy==2.0.41 # Updated to 2.0.41
pydantic==2.7.4
pydantic-settings==2.3.4
pytest==8.2.2
httpx==0.27.0
{% if db_type == "postgresql" %}
psycopg2-binary==2.9.9
{% elif db_type == "mysql" %}
mysql-connector-python==8.4.0
{% elif db_type == "sqlite" %}
# No specific driver needed for sqlite, it's built-in
{% elif db_type == "oracle" %}
cx_Oracle==8.3.0 # or python-oracledb
{% elif db_type == "mssql" %}
pyodbc==5.1.0
{% endif %}
jinja2==3.1.4
"""

# test_router.py.j2
TEST_ROUTER_TEMPLATE = '''
import pytest
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ..main import app
from ..database import Base, get_db
from ..models.{{ table_snake_case }} import {{ table_pascal_case }}

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(name="test_db")
def test_db_fixture():
    """
    Fixture for a test database session.
    Creates tables before tests, drops them after.
    """
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(name="test_client")
def test_client_fixture(test_db):
    """
    Fixture for a test FastAPI client.
    Overrides the get_db dependency to use the test database.
    """
    def override_get_db():
        try:
            yield test_db
        finally:
            test_db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    app.dependency_overrides = {} # Clear overrides after test

# Sample data for testing
sample_{{ table_snake_case }}_data = {
    {% for column in columns %}
    {% if not column.is_primary %}
    "{{ column.name | snake_case }}": {{ CRUDApiGenerator._get_default_value_for_type(column) }},
    {% endif %}
    {% endfor %}
}

updated_{{ table_snake_case }}_data = {
    {% for column in columns %}
    {% if not column.is_primary %}
    "{{ column.name | snake_case }}": {{ CRUDApiGenerator._get_default_value_for_type(column) | replace('_test', '_updated') | replace('1', '2') | replace('1.0', '2.0') | replace('2024-01-01', '2024-01-02') | replace('12:00:00Z', '13:00:00Z') }},
    {% endif %}
    {% endfor %}
}


@pytest.mark.asyncio
async def test_create_{{ table_snake_case }}(test_client):
    """Test creating a new {{ table_snake_case }}."""
    response = await test_client.post("/" + "{{ table_snake_case | pluralize }}", json=sample_{{ table_snake_case }}_data)
    assert response.status_code == 201
    data = response.json()
    assert data["{{ CRUDApiGenerator._get_pk_name(table) | snake_case }}"] is not None
    {% for column in columns %}
    {% if not column.is_primary %}
    assert data["{{ column.name | snake_case }}"] == sample_{{ table_snake_case }}_data["{{ column.name | snake_case }}"]
    {% endif %}
    {% endfor %}

@pytest.mark.asyncio
async def test_read_all_{{ table_snake_case | pluralize }}(test_client):
    """Test reading all {{ table_snake_case | pluralize }}."""
    await test_client.post("/" + "{{ table_snake_case | pluralize }}", json=sample_{{ table_snake_case }}_data)
    response = await test_client.get("/" + "{{ table_snake_case | pluralize }}")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0

@pytest.mark.asyncio
async def test_read_single_{{ table_snake_case }}(test_client):
    """Test reading a single {{ table_snake_case }} by ID."""
    create_response = await test_client.post("/" + "{{ table_snake_case | pluralize }}", json=sample_{{ table_snake_case }}_data)
    {{ CRUDApiGenerator._get_pk_name(table) | snake_case }} = create_response.json()["{{ CRUDApiGenerator._get_pk_name(table) | snake_case }}"]
    
    response = await test_client.get("/" + "{{ table_snake_case | pluralize }}" + "/" + str({{ CRUDApiGenerator._get_pk_name(table) | snake_case }}))
    assert response.status_code == 200
    data = response.json()
    assert data["{{ CRUDApiGenerator._get_pk_name(table) | snake_case }}"] == {{ CRUDApiGenerator._get_pk_name(table) | snake_case }}
    {% for column in columns %}
    {% if not column.is_primary %}
    assert data["{{ column.name | snake_case }}"] == sample_{{ table_snake_case }}_data["{{ column.name | snake_case }}"]
    {% endif %}
    {% endfor %}

@pytest.mark.asyncio
async def test_update_{{ table_snake_case }}(test_client):
    """Test updating an existing {{ table_snake_case }}."""
    create_response = await test_client.post("/" + "{{ table_snake_case | pluralize }}", json=sample_{{ table_snake_case }}_data)
    {{ CRUDApiGenerator._get_pk_name(table) | snake_case }} = create_response.json()["{{ CRUDApiGenerator._get_pk_name(table) | snake_case }}"]

    response = await test_client.put("/" + "{{ table_snake_case | pluralize }}" + "/" + str({{ CRUDApiGenerator._get_pk_name(table) | snake_case }}), json=updated_{{ table_snake_case }}_data)
    assert response.status_code == 200
    data = response.json()
    assert data["{{ CRUDApiGenerator._get_pk_name(table) | snake_case }}"] == {{ CRUDApiGenerator._get_pk_name(table) | snake_case }}
    {% for column in columns %}
    {% if not column.is_primary %}
    assert data["{{ column.name | snake_case }}"] == updated_{{ table_snake_case }}_data["{{ column.name | snake_case }}"]
    {% endif %}
    {% endfor %}

@pytest.mark.asyncio
async def test_delete_{{ table_snake_case }}(test_client):
    """
    Delete a {{ table_snake_case }} record.
    """
    create_response = await test_client.post("/" + "{{ table_snake_case | pluralize }}", json=sample_{{ table_snake_case }}_data)
    {{ CRUDApiGenerator._get_pk_name(table) | snake_case }} = create_response.json()["{{ CRUDApiGenerator._get_pk_name(table) | snake_case }}"]

    response = await test_client.delete("/" + "{{ table_snake_case | pluralize }}" + "/" + str({{ CRUDApiGenerator._get_pk_name(table) | snake_case }}))
    assert response.status_code == 200
    assert response.json()["{{ CRUDApiGenerator._get_pk_name(table) | snake_case }}"] == {{ CRUDApiGenerator._get_pk_name(table) | snake_case }}

    # Verify it's deleted
    get_response = await test_client.get("/" + "{{ table_snake_case | pluralize }}" + "/" + str({{ CRUDApiGenerator._get_pk_name(table) | snake_case }}))
    assert get_response.status_code == 404
'''

# Dockerfile.j2
DOCKERFILE_TEMPLATE = """
# Use a Python base image
FROM python:3.11-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
# Use gunicorn with uvicorn workers for production
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

# .env.example.j2
ENV_EXAMPLE_TEMPLATE = """
# Example environment variables for the backend API
# Copy this file to .env and fill in your actual database URL

# Database connection string
# PostgreSQL Example: DATABASE_URL="postgresql+psycopg2://user:password@localhost:5432/dbname"
# SQLite Example: DATABASE_URL="sqlite:///./sql_app.db"
# MySQL Example: DATABASE_URL="mysql+mysqlconnector://user:password@localhost:3306/dbname"
# SQL Server (MSSQL) Example: DATABASE_URL="mssql+pyodbc://user:password@localhost:1433/dbname?driver=ODBC+Driver+17+for+SQL+Server"
# Oracle Example: DATABASE_URL="oracle+cx_oracle://user:password@localhost:1521/dbname"

DATABASE_URL="{{ 'postgresql+psycopg2://user:password@localhost:5432/dbname' if db_type == 'postgresql' else 'sqlite:///./sql_app.db' }}"
"""


# --- Fullstack Docker Compose Template (Generated in the root directory) ---
DOCKER_COMPOSE_FULLSTACK_TEMPLATE = """
version: '3.8'

services:
  web:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    environment:
      # Set the DATABASE_URL based on the selected db_type
      {% if db_type == "postgresql" %}
      DATABASE_URL: postgresql+psycopg2://user:password@db:5432/mydatabase
      {% elif db_type == "mysql" %}
      DATABASE_URL: mysql+mysqlconnector://user:password@db:3306/mydatabase
      {% elif db_type == "sqlite" %}
      DATABASE_URL: sqlite:///./sql_app.db
      {% else %}
      DATABASE_URL: sqlite:///./sql_app.db # Default to SQLite if db_type is not explicitly handled
      {% endif %}
    depends_on:
      {% if db_type != "sqlite" %}
      - db
      {% endif %}
    # Command to run database migrations/table creation on startup (optional, but good practice)
    # This assumes create_db_and_tables() is idempotent
    command: ["/bin/bash", "-c", "python -c 'from backend.database import create_db_and_tables; create_db_and_tables()' && uvicorn backend.main:app --host 0.0.0.0 --port 8000"]

  frontend:
    build: ./frontend
    ports:
      - "8080:80"
    environment:
      VITE_APP_BACKEND_API_URL: http://web:8000 # Reference the backend service by its name 'web'
    depends_on:
      - web
    volumes:
      - ./frontend:/app # Mount frontend directory for development (optional for production)

  {% if db_type == "postgresql" %}
  db:
    image: postgres:13
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    environment:
      POSTGRES_DB: mydatabase
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
  {% elif db_type == "mysql" %}
  db:
    image: mysql:8.0
    volumes:
      - mysql_data:/var/lib/mysql
    environment:
      MYSQL_ROOT_PASSWORD: password
      MYSQL_DATABASE: mydatabase
      MYSQL_USER: user
      MYSQL_PASSWORD: password
    ports:
      - "3306:3306"
  {% endif %}

volumes:
  {% if db_type == "postgresql" %}
  postgres_data:
  {% elif db_type == "mysql" %}
  mysql_data:
  {% endif %}
"""


def create_template_files_backend(template_dir="templates/backend"):
    """Helper to create dummy template files for demonstration."""
    os.makedirs(template_dir, exist_ok=True)
    with open(os.path.join(template_dir, "model.py.j2"), "w") as f:
        f.write(MODEL_TEMPLATE.strip())
    with open(os.path.join(template_dir, "schema.py.j2"), "w") as f:
        f.write(SCHEMA_TEMPLATE.strip())
    with open(os.path.join(template_dir, "crud.py.j2"), "w") as f:
        f.write(CRUD_TEMPLATE.strip())
    with open(os.path.join(template_dir, "router.py.j2"), "w") as f:
        f.write(ROUTER_TEMPLATE.strip())
    with open(os.path.join(template_dir, "database.py.j2"), "w") as f:
        f.write(DATABASE_TEMPLATE.strip())
    with open(os.path.join(template_dir, "config.py.j2"), "w") as f:
        f.write(CONFIG_TEMPLATE.strip())
    with open(os.path.join(template_dir, "main.py.j2"), "w") as f:
        f.write(MAIN_TEMPLATE.strip())
    with open(os.path.join(template_dir, "requirements.txt.j2"), "w") as f:
        f.write(REQUIREMENTS_TEMPLATE.strip())
    with open(
        os.path.join(template_dir, "test_router.py.j2"), "w"
    ) as f:  # New test template
        f.write(TEST_ROUTER_TEMPLATE.strip())
    with open(
        os.path.join(template_dir, "Dockerfile.j2"), "w"
    ) as f:  # Dockerfile template
        f.write(DOCKERFILE_TEMPLATE.strip())
    with open(
        os.path.join(template_dir, ".env.example.j2"), "w"
    ) as f:  # .env.example template
        f.write(ENV_EXAMPLE_TEMPLATE.strip())
    print(f"Jinja2 backend template files created in '{template_dir}'")


def main_backend_generator(
    tables_to_generate: List[Table],
    db_type: str,
    root_table_names: List[str],
    force_overwrite: bool = False,
):
    create_template_files_backend()
    generator = CRUDApiGenerator(
        tables=tables_to_generate, db_type=db_type, root_table_names=root_table_names
    )
    generator.generate(output_dir="backend", force_overwrite=force_overwrite)


# --- Dummy main_vue_generator for conceptual call ---
# This function will be defined in the separate CRUDVueGenerator Canvas.
# We include a placeholder here to make the main_fullstack_generator runnable in this context.
def main_vue_generator(
    tables_to_generate: List[Table],
    backend_api_url: str,
    root_table_names: List[str],
    force_overwrite: bool = False,
):
    """
    Placeholder for the main_vue_generator function, which will be defined
    in the separate CRUDVueGenerator Canvas.
    In a real execution environment, this would be imported or called from there.
    """
    print("Calling main_vue_generator (defined in a separate Canvas)...")
    # In a real scenario, you would execute the code from the other Canvas here.
    # For this simulated environment, we just acknowledge the call.


# --- Main function to generate both backend and frontend, and the combined docker-compose ---
def main_fullstack_generator(force_overwrite: bool = False):
    # 1. Define your database schema using the provided classes
    # Example: User (parent) and Post (child)
    user_id_col = Column(
        name="id", data_type="integer", is_primary=True, nullable=False
    )
    user_name_col = Column(
        name="name", data_type="varchar", char_length=255, nullable=False
    )
    user_email_col = Column(
        name="email",
        data_type="varchar",
        char_length=255,
        nullable=False,
        constraints=[{"type": "UNIQUE", "name": "uq_user_email"}],
    )
    user_table = Table(name="users")
    user_table.columns["id"] = user_id_col
    user_table.columns["name"] = user_name_col
    user_table.columns["email"] = user_email_col
    user_table.primary_key = PrimaryKey(name="pk_users", columns=["id"])

    post_id_col = Column(
        name="id", data_type="integer", is_primary=True, nullable=False
    )
    post_title_col = Column(
        name="title", data_type="varchar", char_length=255, nullable=False
    )
    post_content_col = Column(name="content", data_type="text", nullable=True)
    post_user_id_col = Column(
        name="user_id",
        data_type="integer",
        nullable=False,
        foreign_key_ref=("", "users", "id"),
    )

    post_table = Table(name="posts")
    post_table.columns["id"] = post_id_col
    post_table.columns["title"] = post_title_col
    post_table.columns["content"] = post_content_col
    post_table.columns["user_id"] = post_user_id_col
    post_table.primary_key = PrimaryKey(name="pk_posts", columns=["id"])
    post_table.foreign_keys.append(
        ForeignKey(
            name="fk_posts_user_id",
            columns=["user_id"],
            ref_table="users",
            ref_columns=["id"],
        )
    )

    tables_to_generate = [user_table, post_table]
    root_tables = ["users"]  # Specify 'users' as a root table to eager-load its posts

    db_type = "postgresql"  # Or "mysql", "sqlite"

    # 2. Generate Backend
    main_backend_generator(
        tables_to_generate, db_type, root_tables, force_overwrite=force_overwrite
    )

    # 3. Generate Frontend (conceptual call to the other Canvas's main function)
    main_vue_generator(
        tables_to_generate,
        "http://web:8000",
        root_tables,
        force_overwrite=force_overwrite,
    )  # backend_api_url points to the 'web' service in docker-compose

    # 4. Generate combined docker-compose.yml in the root directory
    env = Environment(
        loader=FileSystemLoader(os.path.dirname(os.path.abspath(__file__)))
    )
    docker_compose_fullstack_path = os.path.join(os.getcwd(), "docker-compose.yml")
    if os.path.exists(docker_compose_fullstack_path) and not force_overwrite:
        print(f"Skipping existing file: {docker_compose_fullstack_path}")
    else:
        docker_compose_fullstack_template = env.from_string(
            DOCKER_COMPOSE_FULLSTACK_TEMPLATE
        )
        with open(docker_compose_fullstack_path, "w") as f:
            f.write(docker_compose_fullstack_template.render(db_type=db_type))
        print(f"Generated: {docker_compose_fullstack_path}")


if __name__ == "__main__":
    # Run the fullstack generator. Set force_overwrite=True to overwrite all files.
    main_fullstack_generator(force_overwrite=False)
