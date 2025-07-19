import os
from typing import List, Optional, Tuple, Dict
from jinja2 import Environment, FileSystemLoader, select_autoescape
import re


# Re-define Column, PrimaryKey, ForeignKey, Table classes for self-containment
# In a real project, these would be imported from a shared schema definition.
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
        self.foreign_key_ref = foreign_key_ref
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


# Re-define CRUDApiGenerator with static methods for reuse in Vue templates
# This is crucial for the Vue generator to access these utility functions.
class CRUDApiGenerator:
    @staticmethod
    def _to_snake_case(name: str) -> str:
        name = name.replace(" ", "_")
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    @staticmethod
    def _to_pascal_case(name: str) -> str:
        return "".join(word.capitalize() for word in re.split(r"[-_ ]", name))

    @staticmethod
    def _singularize(name: str) -> str:
        if name.endswith("s") and not name.endswith("ss"):
            return name[:-1]
        return name

    @staticmethod
    def _pluralize(name: str) -> str:
        if not name.endswith("s"):
            return name + "s"
        return name

    @staticmethod
    def _sql_type_to_python_type(column: Column) -> str:
        data_type = column.data_type.lower()
        if data_type in ["varchar", "text", "char", "uuid", "json", "jsonb"]:
            return "str"
        elif data_type in ["integer", "smallint", "bigint", "serial", "bigserial"]:
            return "int"
        elif data_type in ["boolean"]:
            return "bool"
        elif data_type in ["float", "double precision", "real", "numeric", "decimal"]:
            return "float"
        elif data_type in ["date"]:
            return "date"
        elif data_type in ["timestamp", "timestamptz", "datetime"]:
            return "datetime"
        elif data_type in ["bytea", "blob"]:
            return "bytes"
        return "Any"

    @staticmethod
    def _get_pydantic_type(column: Column) -> str:
        py_type = CRUDApiGenerator._sql_type_to_python_type(column)
        if py_type == "date":
            py_type = "date"
        elif py_type == "datetime":
            py_type = "datetime"
        elif py_type == "Any":
            return "typing.Any"

        if column.nullable:
            return f"Optional[{py_type}]"
        return py_type

    @staticmethod
    def _get_sqlalchemy_type(column: Column) -> str:
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
        return "String"

    @staticmethod
    def _get_pk_column(table: Table) -> Optional[Column]:
        if table.primary_key and table.primary_key.columns:
            pk_col_name = table.primary_key.columns[0]
            return table.columns.get(pk_col_name)
        return None

    @staticmethod
    def _get_pk_type(table: Table) -> str:
        pk_column = CRUDApiGenerator._get_pk_column(table)
        if pk_column:
            return CRUDApiGenerator._sql_type_to_python_type(pk_column)
        return "int"

    @staticmethod
    def _get_pk_name(table: Table) -> str:
        pk_column = CRUDApiGenerator._get_pk_column(table)
        if pk_column:
            return pk_column.name
        return "id"

    @staticmethod
    def _get_pk_columns(table: Table) -> List[Column]:
        if table.primary_key and table.primary_key.columns:
            return [
                table.columns[col_name]
                for col_name in table.primary_key.columns
                if col_name in table.columns
            ]
        return []

    @staticmethod
    def _get_pk_names_for_repr(table: Table) -> str:
        pk_cols = CRUDApiGenerator._get_pk_columns(table)
        if not pk_cols:
            return "id=None"

        repr_parts = []
        for col in pk_cols:
            repr_parts.append(
                f"{CRUDApiGenerator._to_snake_case(col.name)}={{self.{CRUDApiGenerator._to_snake_case(col.name)}}}"
            )
        return ", ".join(repr_parts)

    @staticmethod
    def _is_auto_generated_pk(column: Column) -> bool:
        if not column.is_primary:
            return False
        data_type = column.data_type.lower()
        if (
            data_type in ["serial", "bigserial", "integer", "smallint", "bigint"]
            and column.default_value is None
        ):
            return True
        if data_type == "uuid" and (
            column.default_value is None
            or "uuid_generate" in str(column.default_value).lower()
        ):
            return True
        return False

    @staticmethod
    def _should_use_server_default(column: Column) -> bool:
        if isinstance(column.default_value, str) and column.default_value.upper() in [
            "CURRENT_TIMESTAMP",
            "NOW()",
            "GETDATE()",
        ]:
            return True
        return False

    # This method needs access to `self.tables` from the generator instance,
    # so it cannot be a static method of CRUDApiGenerator in the same way.
    # It will be passed as a global from the CRUDVueGenerator instance.
    # @staticmethod
    # def _get_child_tables(parent_table: Table, all_tables: List[Table]) -> List[Table]:
    #     children = []
    #     for table in all_tables:
    #         if table.name == parent_table.name:
    #             continue
    #         for fk in table.foreign_keys:
    #             if fk.ref_table == parent_table.name:
    #                 children.append(table)
    #                 break
    #     return children

    @staticmethod
    def _has_datetime_or_date_column(table: Table) -> bool:
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
        data_type = column.data_type.lower()
        if data_type in ["varchar", "text", "char", "uuid", "json", "jsonb"]:
            return f"'{CRUDApiGenerator._to_snake_case(column.name)}_test'"
        elif data_type in ["integer", "smallint", "bigint", "serial", "bigserial"]:
            return 1
        elif data_type in ["boolean"]:
            return "true"  # For JS/Vue, use 'true'/'false'
        elif data_type in ["float", "double precision", "real", "numeric", "decimal"]:
            return 1.0
        elif data_type in ["date"]:
            return "'2024-01-01'"
        elif data_type in ["timestamp", "timestamptz", "datetime"]:
            return "'2024-01-01T12:00:00Z'"
        elif data_type in ["bytea", "blob"]:
            return "'test_bytes'"
        return "'default_value'"

    @staticmethod
    def _js_type(column: Column) -> str:
        """Converts SQL data types to JavaScript types."""
        data_type = column.data_type.lower()
        if data_type in [
            "varchar",
            "text",
            "char",
            "uuid",
            "json",
            "jsonb",
            "date",
            "timestamp",
            "timestamptz",
            "datetime",
            "bytea",
            "blob",
        ]:
            return "string"
        elif data_type in [
            "integer",
            "smallint",
            "bigint",
            "serial",
            "bigserial",
            "float",
            "double precision",
            "real",
            "numeric",
            "decimal",
        ]:
            return "number"
        elif data_type in ["boolean"]:
            return "boolean"
        return "any"  # Fallback

    @staticmethod
    def _js_default_value(column: Column):
        """Returns a suitable default value for JavaScript based on column type."""
        data_type = column.data_type.lower()
        if column.nullable:
            return "null"
        if data_type in [
            "varchar",
            "text",
            "char",
            "uuid",
            "json",
            "jsonb",
            "bytea",
            "blob",
        ]:
            return "''"
        elif data_type in [
            "integer",
            "smallint",
            "bigint",
            "serial",
            "bigserial",
            "float",
            "double precision",
            "real",
            "numeric",
            "decimal",
        ]:
            return 0
        elif data_type in ["boolean"]:
            return "false"
        elif data_type in ["date", "timestamp", "timestamptz", "datetime"]:
            return "''"  # Or 'new Date().toISOString().slice(0, 10)' for date, 'new Date().toISOString()' for datetime
        return "null"

    @staticmethod
    def _js_form_input_type(column: Column) -> str:
        """Returns the appropriate HTML input type for a column."""
        data_type = column.data_type.lower()
        if data_type in [
            "integer",
            "smallint",
            "bigint",
            "serial",
            "bigserial",
            "float",
            "double precision",
            "real",
            "numeric",
            "decimal",
        ]:
            return "number"
        elif data_type == "boolean":
            return "checkbox"
        elif data_type == "date":
            return "date"
        elif data_type in ["timestamp", "timestamptz", "datetime"]:
            return "datetime-local"  # Note: requires specific formatting for input
        elif data_type == "text":
            return "textarea"
        return "text"  # Default for varchar, char, uuid, json, jsonb, bytea, blob

    @staticmethod
    def _is_text_area(column: Column) -> bool:
        return column.data_type.lower() == "text"

    @staticmethod
    def _is_checkbox(column: Column) -> bool:
        return column.data_type.lower() == "boolean"

    @staticmethod
    def _get_vue_model_type(column: Column) -> str:
        # This is for the type of the model property in Vue, which is usually a string or number
        if column.data_type.lower() in [
            "integer",
            "smallint",
            "bigint",
            "serial",
            "bigserial",
            "float",
            "double precision",
            "real",
            "numeric",
            "decimal",
        ]:
            return "number"
        elif column.data_type.lower() == "boolean":
            return "boolean"
        return "string"  # Default for all others

    @staticmethod
    def _get_vue_form_initial_value(column: Column):
        if column.nullable:
            return "null"
        if column.data_type.lower() in [
            "varchar",
            "text",
            "char",
            "uuid",
            "json",
            "jsonb",
            "bytea",
            "blob",
        ]:
            return "''"
        elif column.data_type.lower() in [
            "integer",
            "smallint",
            "bigint",
            "serial",
            "bigserial",
            "float",
            "double precision",
            "real",
            "numeric",
            "decimal",
        ]:
            return 0
        elif column.data_type.lower() == "boolean":
            return "false"
        elif column.data_type.lower() == "date":
            return "''"  # Or a formatted date string
        elif column.data_type.lower() in ["timestamp", "timestamptz", "datetime"]:
            return "''"  # Or a formatted datetime string
        return "null"

    @staticmethod
    def _get_api_endpoint_path(table: Table) -> str:
        return CRUDApiGenerator._pluralize(CRUDApiGenerator._to_snake_case(table.name))


class CRUDVueGenerator:
    """
    Generates a complete Vue 3 frontend application with PrimeVue, Pinia, and Vite.
    """

    def __init__(
        self,
        tables: List[Table],
        backend_api_url: str,
        root_table_names: Optional[List[str]] = None,
    ):
        """
        Args:
            tables: List of Table objects to generate the frontend for.
            backend_api_url: The base URL of the backend API (e.g., "http://localhost:8000").
            root_table_names: A list of table names that should be treated as "root"
                              tables, meaning their list views will be accessible directly
                              from the sidebar.
        """
        self.tables = tables
        self.backend_api_url = backend_api_url
        self.root_table_names = root_table_names if root_table_names is not None else []

        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(current_dir, "templates", "frontend")
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml", "vue", "js"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._add_jinja_globals()

    def _add_jinja_globals(self):
        """Adds custom filters and globals to the Jinja2 environment."""
        # Filters (methods that take an input and transform it)
        self.env.filters["snake_case"] = CRUDApiGenerator._to_snake_case
        self.env.filters["pascal_case"] = CRUDApiGenerator._to_pascal_case
        self.env.filters["singularize"] = CRUDApiGenerator._singularize
        self.env.filters["pluralize"] = CRUDApiGenerator._pluralize

        # Globals (methods that can be called directly like functions in the template)
        self.env.globals["CRUDApiGenerator"] = CRUDApiGenerator  # Pass the class itself
        self.env.globals["get_api_endpoint_path"] = (
            CRUDApiGenerator._get_api_endpoint_path
        )
        self.env.globals["js_type"] = CRUDApiGenerator._js_type
        self.env.globals["js_default_value"] = CRUDApiGenerator._js_default_value
        self.env.globals["js_form_input_type"] = CRUDApiGenerator._js_form_input_type
        self.env.globals["is_text_area"] = CRUDApiGenerator._is_text_area
        self.env.globals["is_checkbox"] = CRUDApiGenerator._is_checkbox
        self.env.globals["get_vue_model_type"] = CRUDApiGenerator._get_vue_model_type
        self.env.globals["get_vue_form_initial_value"] = (
            CRUDApiGenerator._get_vue_form_initial_value
        )
        # Instance methods that need self.tables
        self.env.globals["get_child_tables"] = self._get_child_tables

    def _get_child_tables(self, parent_table: Table) -> List[Table]:
        """Returns a list of tables that have a foreign key referencing the parent_table."""
        children = []
        for table in self.tables:
            if table.name == parent_table.name:
                continue
            for fk in table.foreign_keys:
                if fk.ref_table == parent_table.name:
                    children.append(table)
                    break
        return children

    def generate(self, output_dir: str = "frontend", force_overwrite: bool = False):
        """
        Generates complete frontend structure.

        Args:
            output_dir: The base directory for the generated frontend files.
            force_overwrite: If True, overwrite existing files without prompt.
                             If False, skip existing files.
        """
        base_path = os.path.join(os.getcwd(), output_dir)

        # Create core directories
        os.makedirs(base_path, exist_ok=True)
        os.makedirs(os.path.join(base_path, "src", "views"), exist_ok=True)
        os.makedirs(os.path.join(base_path, "src", "components"), exist_ok=True)
        os.makedirs(os.path.join(base_path, "src", "router"), exist_ok=True)
        os.makedirs(os.path.join(base_path, "src", "stores"), exist_ok=True)
        os.makedirs(os.path.join(base_path, "src", "services"), exist_ok=True)
        os.makedirs(os.path.join(base_path, "src", "tests"), exist_ok=True)
        os.makedirs(os.path.join(base_path, "public"), exist_ok=True)

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
            table_snake_case = CRUDApiGenerator._to_snake_case(table.name)
            table_pascal_case = CRUDApiGenerator._to_pascal_case(table.name)
            pk_name = CRUDApiGenerator._get_pk_name(table)
            pk_type = CRUDApiGenerator._get_pk_type(table)

            context = {
                "table": table,
                "table_snake_case": table_snake_case,
                "table_pascal_case": table_pascal_case,
                "pk_name": pk_name,
                "pk_type": pk_type,
                "columns": list(table.columns.values()),
                "backend_api_url": self.backend_api_url,
                "all_tables": self.tables,  # Pass all tables for relationships
                "is_root_table": table.name in self.root_table_names,
            }

            # Generate List View
            list_view_template = self.env.get_template("ListView.vue.j2")
            list_view_content = list_view_template.render(context)
            write_file(
                os.path.join(
                    base_path, "src", "views", f"{table_pascal_case}ListView.vue"
                ),
                list_view_content,
            )

            # Generate Form View
            form_view_template = self.env.get_template("FormView.vue.j2")
            form_view_content = form_view_template.render(context)
            write_file(
                os.path.join(
                    base_path, "src", "views", f"{table_pascal_case}FormView.vue"
                ),
                form_view_content,
            )

            # Generate Pinia Store
            store_template = self.env.get_template("store.js.j2")
            store_content = store_template.render(context)
            write_file(
                os.path.join(base_path, "src", "stores", f"{table_snake_case}Store.js"),
                store_content,
            )

            # Generate API Service
            service_template = self.env.get_template("service.js.j2")
            service_content = service_template.render(context)
            write_file(
                os.path.join(
                    base_path, "src", "services", f"{table_snake_case}Service.js"
                ),
                service_content,
            )

            # Generate Unit Test
            test_template = self.env.get_template("test.js.j2")
            test_content = test_template.render(context)
            write_file(
                os.path.join(base_path, "src", "tests", f"{table_snake_case}.test.js"),
                test_content,
            )

        # Generate core files (overwrite always for these)
        core_context = {
            "tables": self.tables,
            "root_table_names": self.root_table_names,
            "backend_api_url": self.backend_api_url,
        }

        # App.vue
        app_vue_template = self.env.get_template("App.vue.j2")
        write_file(
            os.path.join(base_path, "src", "App.vue"),
            app_vue_template.render(core_context),
            overwrite_always=True,
        )

        # main.js
        main_js_template = self.env.get_template("main.js.j2")
        write_file(
            os.path.join(base_path, "src", "main.js"),
            main_js_template.render(core_context),
            overwrite_always=True,
        )

        # router/index.js
        router_index_template = self.env.get_template("router_index.js.j2")
        write_file(
            os.path.join(base_path, "src", "router", "index.js"),
            router_index_template.render(core_context),
            overwrite_always=True,
        )

        # package.json
        package_json_template = self.env.get_template("package.json.j2")
        write_file(
            os.path.join(base_path, "package.json"),
            package_json_template.render(core_context),
            overwrite_always=True,
        )

        # vite.config.js
        vite_config_template = self.env.get_template("vite.config.js.j2")
        write_file(
            os.path.join(base_path, "vite.config.js"),
            vite_config_template.render(core_context),
            overwrite_always=True,
        )

        # index.html
        index_html_template = self.env.get_template("index.html.j2")
        write_file(
            os.path.join(base_path, "index.html"),
            index_html_template.render(core_context),
            overwrite_always=True,
        )

        # README.md
        readme_template = self.env.get_template("README.md.j2")
        write_file(
            os.path.join(base_path, "README.md"),
            readme_template.render(core_context),
            overwrite_always=True,
        )

        print(
            f"Frontend application generated successfully in '{output_dir}' directory."
        )


# --- Jinja2 Templates for Vue Frontend ---

# ListView.vue.j2
LIST_VIEW_TEMPLATE = """
<template>
  <div class="card">
    <Toolbar class="mb-4">
      <template #start>
        <Button label="New" icon="pi pi-plus" severity="success" class="mr-2" @click="openNew" />
        <Button label="Delete" icon="pi pi-trash" severity="danger" @click="confirmDeleteSelected" :disabled="!selected{{ table_pascal_case }}s || !selected{{ table_pascal_case }}s.length" />
      </template>
      <template #end>
        <FileUpload mode="basic" accept="image/*" :maxFileSize="1000000" label="Import" chooseLabel="Import" class="mr-2 inline-block" />
        <Button label="Export" icon="pi pi-upload" severity="help" @click="exportCSV($event)" />
      </template>
    </Toolbar>

    <DataTable ref="dt" :value="{{ table_snake_case | pluralize }}" v-model:selection="selected{{ table_pascal_case }}s" dataKey="{{ pk_name | snake_case }}"
      :paginator="true" :rows="10" :filters="filters"
      paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
      :rowsPerPageOptions="[5,10,25]" currentPageReportTemplate="Showing {first} to {last} of {totalRecords} {{ table_snake_case | pluralize }}">
      <Column selectionMode="multiple" style="width: 3rem" :exportable="false"></Column>
      {% for column in columns %}
      <Column field="{{ column.name | snake_case }}" header="{{ column.name | pascal_case }}" sortable style="min-width:12rem"></Column>
      {% endfor %}
      <Column :exportable="false" style="min-width:8rem">
        <template #body="slotProps">
          <Button icon="pi pi-pencil" severity="success" class="mr-2" @click="edit{{ table_pascal_case }}(slotProps.data)" />
          <Button icon="pi pi-trash" severity="warning" @click="confirmDelete{{ table_pascal_case }}(slotProps.data)" />
        </template>
      </Column>
    </DataTable>
  </div>

  <Dialog v-model:visible="{{ table_snake_case }}Dialog" :style="{width: '450px'}" header="{{ table_pascal_case }} Details" :modal="true" class="p-fluid">
    <div class="field">
      <label for="{{ pk_name | snake_case }}">{{ pk_name | pascal_case }}</label>
      <InputText id="{{ pk_name | snake_case }}" v-model.trim="new{{ table_pascal_case }}.{{ pk_name | snake_case }}" required="true" autofocus :class="{'p-invalid': submitted && !new{{ table_pascal_case }}.{{ pk_name | snake_case }}" />
      <small class="p-error" v-if="submitted && !new{{ table_pascal_case }}.{{ pk_name | snake_case }}">ID is required.</small>
    </div>
    {% for column in columns %}
    {% if not column.is_primary %}
    <div class="field">
      <label for="{{ column.name | snake_case }}">{{ column.name | pascal_case }}</label>
      {% if CRUDApiGenerator._is_text_area(column) %}
      <Textarea id="{{ column.name | snake_case }}" v-model="new{{ table_pascal_case }}.{{ column.name | snake_case }}" rows="3" cols="20" />
      {% elif CRUDApiGenerator._is_checkbox(column) %}
      <Checkbox id="{{ column.name | snake_case }}" v-model="new{{ table_pascal_case }}.{{ column.name | snake_case }}" :binary="true" />
      {% else %}
      <InputText 
        id="{{ column.name | snake_case }}" 
        v-model="new{{ table_pascal_case }}.{{ column.name | snake_case }}" 
        {% if CRUDApiGenerator._get_vue_model_type(column) == 'number' %}@input="new{{ table_pascal_case }}.{{ column.name | snake_case }} = parseFloat($event.target.value)"{% endif %}
        :type="CRUDApiGenerator._js_form_input_type(column)" 
      />
      {% endif %}
    </div>
    {% endif %}
    {% endfor %}

    <template #footer>
      <Button label="Cancel" icon="pi pi-times" text @click="hideDialog"/>
      <Button label="Save" icon="pi pi-check" text @click="save{{ table_pascal_case }}"/>
    </template>
  </Dialog>

  <Dialog v-model:visible="delete{{ table_pascal_case }}Dialog" :style="{width: '450px'}" header="Confirm" :modal="true">
    <div class="confirmation-content">
      <i class="pi pi-exclamation-triangle mr-3" style="font-size: 2rem" />
      <span v-if="new{{ table_pascal_case }}">Are you sure you want to delete <b>{{ 'new' + table_pascal_case + '.' + pk_name }}</b>?</span>
    </div>
    <template #footer>
      <Button label="No" icon="pi pi-times" text @click="delete{{ table_pascal_case }}Dialog = false"/>
      <Button label="Yes" icon="pi pi-check" text @click="delete{{ table_pascal_case }}"/>
    </template>
  </Dialog>

  <Dialog v-model:visible="delete{{ table_pascal_case }}sDialog" :style="{width: '450px'}" header="Confirm" :modal="true">
    <div class="confirmation-content">
      <i class="pi pi-exclamation-triangle mr-3" style="font-size: 2rem" />
      <span v-if="new{{ table_pascal_case }}s">Are you sure you want to delete the selected {{ table_snake_case | pluralize }}?</span>
    </div>
    <template #footer>
      <Button label="No" icon="pi pi-times" text @click="delete{{ table_pascal_case }}sDialog = false"/>
      <Button label="Yes" icon="pi pi-check" text @click="deleteSelected{{ table_pascal_case }}s"/>
    </template>
  </Dialog>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { use{{ table_pascal_case }}Store } from '@/stores/{{ table_snake_case }}Store.js';
import { FilterMatchMode } from 'primevue/api';
import { useToast } from 'primevue/usetoast';

const toast = useToast();
const store = use{{ table_pascal_case }}Store();
const dt = ref(null);
const {{ table_snake_case | pluralize }} = ref([]);
const {{ table_snake_case }}Dialog = ref(false);
const delete{{ table_pascal_case }}Dialog = ref(false);
const delete{{ table_pascal_case }}sDialog = ref(false);
const new{{ table_pascal_case }} = ref({});
const selected{{ table_pascal_case }}s = ref(null);
const filters = ref({});
const submitted = ref(false);

onMounted(async () => {
  await store.fetch{{ table_pascal_case }}s();
  {{ table_snake_case | pluralize }}.value = store.get{{ table_pascal_case }}s;
});

watch(() => store.get{{ table_pascal_case }}s, (newVal) => {
  {{ table_snake_case | pluralize }}.value = newVal;
});

const openNew = () => {
  new{{ table_pascal_case }}.value = {
    {% for column in columns %}
    {{ column.name | snake_case }}: {{ CRUDApiGenerator._get_vue_form_initial_value(column) }},
    {% endfor %}
  };
  submitted.value = false;
  {{ table_snake_case }}Dialog.value = true;
};

const hideDialog = () => {
  {{ table_snake_case }}Dialog.value = false;
  submitted.value = false;
};

const save{{ table_pascal_case }} = async () => {
  submitted.value = true;
  if (new{{ table_pascal_case }}.value.{{ pk_name | snake_case }}) {
    // Update existing
    await store.update{{ table_pascal_case }}(new{{ table_pascal_case }}.value.{{ pk_name | snake_case }}, new{{ table_pascal_case }}.value);
    toast.add({severity:'success', summary: 'Successful', detail: '{{ table_pascal_case }} Updated', life: 3000});
  } else {
    // Create new
    await store.create{{ table_pascal_case }}(new{{ table_pascal_case }}.value);
    toast.add({severity:'success', summary: 'Successful', detail: '{{ table_pascal_case }} Created', life: 3000});
  }
  {{ table_snake_case }}Dialog.value = false;
  new{{ table_pascal_case }}.value = {};
};

const edit{{ table_pascal_case }} = (prod) => {
  new{{ table_pascal_case }}.value = {...prod};
  {{ table_snake_case }}Dialog.value = true;
};

const confirmDelete{{ table_pascal_case }} = (prod) => {
  new{{ table_pascal_case }}.value = prod;
  delete{{ table_pascal_case }}Dialog.value = true;
};

const delete{{ table_pascal_case }} = async () => {
  await store.delete{{ table_pascal_case }}(new{{ table_pascal_case }}.value.{{ pk_name | snake_case }});
  delete{{ table_pascal_case }}Dialog.value = false;
  {{ table_snake_case }}.value = {{ table_snake_case }}.value.filter(val => val.{{ pk_name | snake_case }} !== new{{ table_pascal_case }}.value.{{ pk_name | snake_case }});
  toast.add({severity:'success', summary: 'Successful', detail: '{{ table_pascal_case }} Deleted', life: 3000});
  new{{ table_pascal_case }}.value = {};
};

const exportCSV = () => {
  dt.value.exportCSV();
};

const confirmDeleteSelected = () => {
  delete{{ table_pascal_case }}sDialog.value = true;
};

const deleteSelected{{ table_pascal_case }}s = async () => {
  for (const prod of selected{{ table_pascal_case }}s.value) {
    await store.delete{{ table_pascal_case }}(prod.{{ pk_name | snake_case }});
  }
  {{ table_snake_case | pluralize }}.value = {{ table_snake_case | pluralize }}.value.filter(val => !selected{{ table_pascal_case }}s.value.includes(val));
  delete{{ table_pascal_case }}sDialog.value = false;
  selected{{ table_pascal_case }}s.value = null;
  toast.add({severity:'success', summary: 'Successful', detail: 'Selected {{ table_pascal_case }}s Deleted', life: 3000});
};

const initFilters = () => {
  filters.value = {
    'global': {value: null, matchMode: FilterMatchMode.CONTAINS},
  };
};

initFilters();
</script>

<style scoped>
/* Add your component-specific styles here */
</style>
"""

# FormView.vue.j2
FORM_VIEW_TEMPLATE = """
<template>
  <div class="card">
    <h2>{{ table_pascal_case }} Form</h2>
    <form @submit.prevent="handleSubmit">
      {% for column in columns %}
      <div class="p-field mb-3">
        <label for="{{ column.name | snake_case }}" class="block text-900 font-medium mb-2">{{ column.name | pascal_case }}</label>
        {% if CRUDApiGenerator._is_text_area(column) %}
        <Textarea :id="`{{ column.name | snake_case }}`" v-model="formData.{{ column.name | snake_case }}" rows="3" class="w-full" />
        {% elif CRUDApiGenerator._is_checkbox(column) %}
        <Checkbox :id="`{{ column.name | snake_case }}`" v-model="formData.{{ column.name | snake_case }}" :binary="true" />
        {% else %}
        <InputText 
          :id="`{{ column.name | snake_case }}`" 
          v-model="formData.{{ column.name | snake_case }}" 
          {% if CRUDApiGenerator._get_vue_model_type(column) == 'number' %}@input="formData.{{ column.name | snake_case }} = parseFloat($event.target.value)"{% endif %}
          :type="CRUDApiGenerator._js_form_input_type(column)" 
          class="w-full" 
        />
        {% endif %}
      </div>
      {% endfor %}

      <Button type="submit" label="Save" class="p-button-primary mr-2" />
      <Button label="Cancel" class="p-button-secondary" @click="handleCancel" />
    </form>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { use{{ table_pascal_case }}Store } from '@/stores/{{ table_snake_case }}Store.js';

const route = useRoute();
const router = useRouter();
const toast = useToast();
const store = use{{ table_pascal_case }}Store();

const formData = ref({
  {% for column in columns %}
  {{ column.name | snake_case }}: {{ CRUDApiGenerator._get_vue_form_initial_value(column) }},
  {% endfor %}
});

const isEditMode = ref(false);

onMounted(async () => {
  const {{ pk_name | snake_case }} = route.params.{{ pk_name | snake_case }};
  if ({{ pk_name | snake_case }}) {
    isEditMode.value = true;
    const {{ table_snake_case }}Data = await store.fetch{{ table_pascal_case }}ById({{ pk_name | snake_case }});
    if ({{ table_snake_case }}Data) {
      formData.value = { ...{{ table_snake_case }}Data };
    } else {
      toast.add({severity:'error', summary: 'Error', detail: '{{ table_pascal_case }} not found', life: 3000});
      router.push('/{{ get_api_endpoint_path(table) }}');
    }
  }
});

const handleSubmit = async () => {
  try {
    if (isEditMode.value) {
      await store.update{{ table_pascal_case }}(route.params.{{ pk_name | snake_case }}, formData.value);
      toast.add({severity:'success', summary: 'Success', detail: '{{ table_pascal_case }} updated successfully!', life: 3000});
    } else {
      await store.create{{ table_pascal_case }}(formData.value);
      toast.add({severity:'success', summary: 'Success', detail: '{{ table_pascal_case }} created successfully!', life: 3000});
    }
    router.push('/{{ get_api_endpoint_path(table) }}');
  } catch (error) {
    toast.add({severity:'error', summary: 'Error', detail: 'Failed to save {{ table_snake_case }}: ' + error.message, life: 3000});
  }
};

const handleCancel = () => {
  router.push('/{{ get_api_endpoint_path(table) }}');
};
</script>

<style scoped>
/* Add your component-specific styles here */
</style>
"""

# store.js.j2
STORE_TEMPLATE = """
import { defineStore } from 'pinia';
import * as {{ table_snake_case }}Service from '@/services/{{ table_snake_case }}Service.js';

export const use{{ table_pascal_case }}Store = defineStore('{{ table_snake_case }}', {
  state: () => ({
    {{ table_snake_case | pluralize }}: [],
    current{{ table_pascal_case }}: null,
    loading: false,
    error: null,
  }),
  getters: {
    get{{ table_pascal_case }}s: (state) => state.{{ table_snake_case | pluralize }},
    get{{ table_pascal_case }}ById: (state) => (id) => state.{{ table_snake_case | pluralize }}.find({{ table_snake_case }} => {{ table_snake_case }}.{{ pk_name | snake_case }} === id),
  },
  actions: {
    async fetch{{ table_pascal_case }}s() {
      this.loading = true;
      try {
        const response = await {{ table_snake_case }}Service.getAll{{ table_pascal_case }}s();
        this.{{ table_snake_case | pluralize }} = response.data;
      } catch (error) {
        this.error = error;
        console.error('Error fetching {{ table_snake_case | pluralize }}:', error);
      } finally {
        this.loading = false;
      }
    },
    async fetch{{ table_pascal_case }}ById(id) {
      this.loading = true;
      try {
        const response = await {{ table_snake_case }}Service.get{{ table_pascal_case }}ById(id);
        this.current{{ table_pascal_case }} = response.data;
        return response.data;
      } catch (error) {
        this.error = error;
        console.error('Error fetching {{ table_snake_case }} by ID:', error);
        return null;
      } finally {
        this.loading = false;
      }
    },
    async create{{ table_pascal_case }}({{ table_snake_case }}Data) {
      this.loading = true;
      try {
        const response = await {{ table_snake_case }}Service.create{{ table_pascal_case }}({{ table_snake_case }}Data);
        this.{{ table_snake_case | pluralize }}.push(response.data);
      } catch (error) {
        this.error = error;
        console.error('Error creating {{ table_snake_case }}:', error);
        throw error;
      } finally {
        this.loading = false;
      }
    },
    async update{{ table_pascal_case }}(id, {{ table_snake_case }}Data) {
      this.loading = true;
      try {
        const response = await {{ table_snake_case }}Service.update{{ table_pascal_case }}(id, {{ table_snake_case }}Data);
        const index = this.{{ table_snake_case | pluralize }}.findIndex({{ table_snake_case }} => {{ table_snake_case }}.{{ pk_name | snake_case }} === id);
        if (index !== -1) {
          this.{{ table_snake_case | pluralize }}[index] = response.data;
        }
      } catch (error) {
        this.error = error;
        console.error('Error updating {{ table_snake_case }}:', error);
        throw error;
      } finally {
        this.loading = false;
      }
    },
    async delete{{ table_pascal_case }}(id) {
      this.loading = true;
      try {
        await {{ table_snake_case }}Service.delete{{ table_pascal_case }}(id);
        this.{{ table_snake_case | pluralize }} = this.{{ table_snake_case | pluralize }}.filter({{ table_snake_case }} => {{ table_snake_case }}.{{ pk_name | snake_case }} !== id);
      } catch (error) {
        this.error = error;
        console.error('Error deleting {{ table_snake_case }}:', error);
        throw error;
      } finally {
        this.loading = false;
      }
      },
  },
});
"""

# service.js.j2
SERVICE_TEMPLATE = """
import axios from 'axios';

const API_URL = import.meta.env.VITE_APP_BACKEND_API_URL || '{{ backend_api_url }}';

const {{ table_snake_case | pluralize }}Api = axios.create({
  baseURL: `${API_URL}/{{ CRUDApiGenerator._get_api_endpoint_path(table) }}`,
});

export const getAll{{ table_pascal_case }}s = () => {
  return {{ table_snake_case | pluralize }}Api.get('/');
};

export const get{{ table_pascal_case }}ById = (id) => {
  return {{ table_snake_case | pluralize }}Api.get(`/${id}`);
};

export const create{{ table_pascal_case }} = ({{ table_snake_case }}Data) => {
  return {{ table_snake_case | pluralize }}Api.post('/', {{ table_snake_case }}Data);
};

export const update{{ table_pascal_case }} = (id, {{ table_snake_case }}Data) => {
  return {{ table_snake_case | pluralize }}Api.put(`/${id}`, {{ table_snake_case }}Data);
};

export const delete{{ table_pascal_case }} = (id) => {
  return {{ table_snake_case | pluralize }}Api.delete(`/${id}`);
};
"""

# test.js.j2
TEST_TEMPLATE = """
import { setActivePinia, createPinia } from 'pinia';
import { use{{ table_pascal_case }}Store } from '@/stores/{{ table_snake_case }}Store.js';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import * as {{ table_snake_case }}Service from '@/services/{{ table_snake_case }}Service.js';

// Mock the service layer
vi.mock('@/services/{{ table_snake_case }}Service.js', () => ({
  getAll{{ table_pascal_case }}s: vi.fn(),
  get{{ table_pascal_case }}ById: vi.fn(),
  create{{ table_pascal_case }}: vi.fn(),
  update{{ table_pascal_case }}: vi.fn(),
  delete{{ table_pascal_case }}: vi.fn(),
}));

describe('{{ table_pascal_case }} Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    // Reset mocks before each test
    vi.clearAllMocks();
  });

  const mock{{ table_pascal_case }} = {
    {{ pk_name | snake_case }}: 1,
    {% for column in columns %}
    {% if not column.is_primary %}
    {{ column.name | snake_case }}: {{ CRUDApiGenerator._get_default_value_for_type(column) }},
    {% endif %}
    {% endfor %}
  };

  it('fetches all {{ table_snake_case | pluralize }}', async () => {
    {{ table_snake_case }}Service.getAll{{ table_pascal_case }}s.mockResolvedValue({ data: [mock{{ table_pascal_case }}] });
    const store = use{{ table_pascal_case }}Store();
    await store.fetch{{ table_pascal_case }}s();
    expect(store.{{ table_snake_case | pluralize }}).toEqual([mock{{ table_pascal_case }}]);
    expect(store.loading).toBe(false);
  });

  it('fetches {{ table_snake_case }} by ID', async () => {
    {{ table_snake_case }}Service.get{{ table_pascal_case }}ById.mockResolvedValue({ data: mock{{ table_pascal_case }} });
    const store = use{{ table_pascal_case }}Store();
    const fetched{{ table_pascal_case }} = await store.fetch{{ table_pascal_case }}ById(1);
    expect(fetched{{ table_pascal_case }}).toEqual(mock{{ table_pascal_case }});
    expect(store.current{{ table_pascal_case }}).toEqual(mock{{ table_pascal_case }});
    expect(store.loading).toBe(false);
  });

  it('creates a new {{ table_snake_case }}', async () => {
    const new{{ table_pascal_case }}Data = {
      {% for column in columns %}
      {% if not column.is_primary %}
      {{ column.name | snake_case }}: {{ CRUDApiGenerator._get_default_value_for_type(column) | replace('_test', '_new') }},
      {% endif %}
      {% endfor %}
    };
    const created{{ table_pascal_case }} = { ...new{{ table_pascal_case }}Data, {{ pk_name | snake_case }}: 2 };
    {{ table_snake_case }}Service.create{{ table_pascal_case }}.mockResolvedValue({ data: created{{ table_pascal_case }} });

    const store = use{{ table_pascal_case }}Store();
    store.{{ table_snake_case | pluralize }} = []; // Ensure empty state
    await store.create{{ table_pascal_case }}(new{{ table_pascal_case }}Data);
    expect(store.{{ table_snake_case | pluralize }}).toContainEqual(created{{ table_pascal_case }});
    expect(store.loading).toBe(false);
  });

  it('updates an existing {{ table_snake_case }}', async () => {
    const updatedData = { ...mock{{ table_pascal_case }},
      {% for column in columns %}
      {% if not column.is_primary %}
      {{ column.name | snake_case }}: {{ CRUDApiGenerator._get_default_value_for_type(column) | replace('_test', '_updated') }},
      {% endif %}
      {% endfor %}
    };
    {{ table_snake_case }}Service.update{{ table_pascal_case }}.mockResolvedValue({ data: updatedData });

    const store = use{{ table_pascal_case }}Store();
    store.{{ table_snake_case | pluralize }} = [mock{{ table_pascal_case }}]; // Seed with initial data
    await store.update{{ table_pascal_case }}(mock{{ table_pascal_case }}.{{ pk_name | snake_case }}, updatedData);
    expect(store.{{ table_snake_case | pluralize }}).toContainEqual(updatedData);
    expect(store.loading).toBe(false);
  });

  it('deletes a {{ table_snake_case }}', async () => {
    {{ table_snake_case }}Service.delete{{ table_pascal_case }}.mockResolvedValue({});

    const store = use{{ table_pascal_case }}Store();
    store.{{ table_snake_case | pluralize }} = [mock{{ table_pascal_case }}]; // Seed with initial data
    await store.delete{{ table_pascal_case }}(mock{{ table_pascal_case }}.{{ pk_name | snake_case }});
    expect(store.{{ table_snake_case | pluralize }}).not.toContainEqual(mock{{ table_pascal_case }});
    expect(store.loading).toBe(false);
  });

  it('handles API errors during fetch', async () => {
    const error = new Error('Network error');
    {{ table_snake_case }}Service.getAll{{ table_pascal_case }}s.mockRejectedValue(error);

    const store = use{{ table_pascal_case }}Store();
    await store.fetch{{ table_pascal_case }}s();
    expect(store.error).toBe(error);
    expect(store.loading).toBe(false);
  });
});
"""

# App.vue.j2
APP_VUE_TEMPLATE = """
<template>
  <div class="min-h-screen flex flex-col">
    <Toast />
    <Menubar :model="items" class="p-3 shadow-2">
      <template #start>
        <h3 class="font-bold text-xl mr-4">My App</h3>
      </template>
      <template #end>
        <InputText placeholder="Search" type="text" />
      </template>
    </Menubar>

    <div class="flex flex-grow">
      <PanelMenu :model="sidebarItems" class="w-full md:w-20rem sidebar-menu" />
      <div class="p-4 flex-grow">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import Toast from 'primevue/toast';
import Menubar from 'primevue/menubar';
import PanelMenu from 'primevue/panelmenu';
import InputText from 'primevue/inputtext';

const router = useRouter();

const items = ref([
  {
    label: 'Home',
    icon: 'pi pi-home',
    command: () => { router.push('/'); }
  },
  {% for table in tables %}
  {% if table.name in root_table_names %}
  {
    label: '{{ table.name | pascal_case | pluralize }}',
    icon: 'pi pi-table',
    command: () => { router.push('/{{ CRUDApiGenerator._to_snake_case(table.name) | pluralize }}'); }
  },
  {% endif %}
  {% endfor %}
]);

const sidebarItems = ref([
  {
    label: 'Entities',
    icon: 'pi pi-database',
    items: [
      {% for table in tables %}
      {
        label: '{{ table.name | pascal_case | pluralize }}',
        icon: 'pi pi-list',
        to: '/{{ CRUDApiGenerator._to_snake_case(table.name) | pluralize }}'
      },
      {
        label: 'Add {{ table.name | pascal_case }}',
        icon: 'pi pi-plus',
        to: '/{{ CRUDApiGenerator._to_snake_case(table.name) | pluralize }}/new'
      },
      {% endfor %}
    ]
  },
]);
</script>

<style>
@import 'primevue/resources/themes/saga-blue/theme.css';
@import 'primevue/resources/primevue.min.css';
@import 'primeicons/primeicons.css';
@import 'primeflex/primeflex.css'; /* For PrimeFlex utilities */

body {
  font-family: 'Inter', sans-serif;
  margin: 0;
  background-color: var(--surface-ground);
}

#app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.sidebar-menu {
  flex-shrink: 0;
  width: 15rem; /* Adjust width as needed */
  background-color: var(--surface-card);
  border-right: 1px solid var(--surface-border);
}

.p-panelmenu .p-panelmenu-header .p-toggleable-content {
    padding: 0;
}

.p-panelmenu .p-menuitem-link {
    padding: 0.75rem 1rem;
}

.p-menubar {
  border-radius: 0;
}
</style>
"""

# main.js.j2
MAIN_JS_TEMPLATE = """
import { createApp } from 'vue';
import App from './App.vue';
import router from './router';
import { createPinia } from 'pinia';

// PrimeVue
import PrimeVue from 'primevue/config';
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import Toast from 'primevue/toast';
import ToastService from 'primevue/toastservice';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Toolbar from 'primevue/toolbar';
import Dialog from 'primevue/dialog';
import FileUpload from 'primevue/fileupload';
import Textarea from 'primevue/textarea';
import Checkbox from 'primevue/checkbox';
import Menubar from 'primevue/menubar';
import PanelMenu from 'primevue/panelmenu';


const app = createApp(App);

app.use(createPinia());
app.use(router);
app.use(PrimeVue);
app.use(ToastService);

// Register PrimeVue components globally
app.component('Button', Button);
app.component('InputText', InputText);
app.component('Toast', Toast);
app.component('DataTable', DataTable);
app.component('Column', Column);
app.component('Toolbar', Toolbar);
app.component('Dialog', Dialog);
app.component('FileUpload', FileUpload);
app.component('Textarea', Textarea);
app.component('Checkbox', Checkbox);
app.component('Menubar', Menubar);
app.component('PanelMenu', PanelMenu);


app.mount('#app');
"""

# router_index.js.j2
ROUTER_INDEX_TEMPLATE = """
import { createRouter, createWebHistory } from 'vue-router';
{% for table in tables %}
import {{ table.name | pascal_case }}ListView from '@/views/{{ table.name | pascal_case }}ListView.vue';
import {{ table.name | pascal_case }}FormView from '@/views/{{ table.name | pascal_case }}FormView.vue';
{% endfor %}

const routes = [
  {
    path: '/',
    name: 'home',
    redirect: '/{{ CRUDApiGenerator._to_snake_case(tables[0].name) | pluralize }}' // Redirect to the first table's list view
  },
  {% for table in tables %}
  {
    path: '/{{ CRUDApiGenerator._to_snake_case(table.name) | pluralize }}',
    name: '{{ table.name | snake_case | pluralize }}',
    component: {{ table.name | pascal_case }}ListView,
  },
  {
    path: '/{{ CRUDApiGenerator._to_snake_case(table.name) | pluralize }}/new',
    name: 'new-{{ table.name | snake_case }}',
    component: {{ table.name | pascal_case }}FormView,
  },
  {
    path: '/{{ CRUDApiGenerator._to_snake_case(table.name) | pluralize }}/:{{ CRUDApiGenerator._get_pk_name(table) | snake_case }}',
    name: 'edit-{{ table.name | snake_case }}',
    component: {{ table.name | pascal_case }}FormView,
    props: true,
  },
  {% endfor %}
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
"""

# package.json.j2
PACKAGE_JSON_TEMPLATE = """
{
  "name": "frontend",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test:unit": "vitest"
  },
  "dependencies": {
    "axios": "^1.7.2",
    "pinia": "^2.1.7",
    "primeicons": "^7.0.0",
    "primevue": "^3.52.0",
    "vue": "^3.4.21",
    "vue-router": "^4.3.2"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.4",
    "@vue/test-utils": "^2.4.6",
    "jsdom": "^24.0.0",
    "vite": "^5.2.0",
    "vitest": "^1.6.0"
  }
}
"""

# vite.config.js.j2
VITE_CONFIG_TEMPLATE = """
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'path'; // Import path module

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
  ],
  resolve: {
    alias: {
      // Use path.resolve with process.cwd() for more robust path resolution
      '@': path.resolve(process.cwd(), 'src')
    }
  },
  server: {
    port: 8080,
  },
  test: {
    environment: 'jsdom',
  },
});
"""

# index.html.j2
INDEX_HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" href="/favicon.ico" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Vite Vue App</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
"""

# README.md.j2
README_TEMPLATE = """
# Frontend Application

This project provides a dynamic and interactive frontend application built with **Vue 3**, styled with **PrimeVue** components, and managed with **Pinia** for state management. It's built using **Vite** for a fast development experience.

## Features

* **Vue 3**: Progressive JavaScript framework for building user interfaces.
* **PrimeVue**: A rich set of UI components for Vue.js, providing a professional and responsive design.
* **Pinia**: The official state management library for Vue.js.
* **Vue Router**: For declarative routing within the single-page application.
* **Vite**: Next-generation frontend tooling for a blazing fast development setup.
* **SBAdmin/Material Design Layout**: Provides a clean, responsive, and consistent administrative panel look and feel.
* **CRUD Interfaces**: Dedicated views for each database table, enabling Create, Read, Update, and Delete operations.
* **Vitest Unit Tests**: Automated unit tests for Vue components and Pinia stores.

## Setup

Follow these steps to get your frontend application up and running.

### Prerequisites

* Node.js (LTS version recommended)
* npm or Yarn package manager

### Installation

1.  **Navigate to your `frontend` directory:**

    ```bash
    cd frontend
    ```

2.  **Install Node.js dependencies:**

    ```bash
    npm install # or yarn install
    ```

### Running the Application

1.  **Start the development server:**

    ```bash
    npm run dev # or yarn dev
    ```

    The application will typically be available at `http://localhost:5173`.

    * Ensure your backend API is running concurrently for full functionality.

### Building for Production

To build the application for production deployment:

```bash
npm run build # or yarn build
```

This command will compile and minify your application into the `dist/` directory, ready for deployment.

### Project Structure

* `src/`: Main application source code
    * `views/`: Vue components representing full pages (e.g., `UserView.vue`).
    * `components/`: Reusable smaller Vue components.
    * `router/`: Vue Router configuration.
    * `store/`: Pinia state management modules.
    * `services/`: API client services for interacting with the backend.
    * `tests/`: Vitest unit tests.
    * `App.vue`: The main application layout.
    * `main.js`: The application's entry point.
* `public/`: Static assets (e.g., `index.html`, `favicon.ico`).
* `package.json`: Project metadata and dependencies.

## Available Scripts

In the project directory, you can run:

* `npm run dev`: Runs the app in development mode.
* `npm run build`: Builds the app for production to the `dist` folder.
* `npm run preview`: Serves the `dist` folder in production mode.
* `npm run test:unit`: Runs unit tests with Vitest.

## Testing

Unit tests are generated using `Vitest`.

1.  **Ensure all Node.js dependencies are installed.**
2.  **Run tests from the `frontend/` directory:**
    ```bash
    npm run test:unit # or yarn test:unit
    ```
"""


def create_template_files_frontend(template_dir="templates/frontend"):
    """Helper to create dummy template files for frontend demonstration."""
    os.makedirs(template_dir, exist_ok=True)
    with open(os.path.join(template_dir, "ListView.vue.j2"), "w") as f:
        f.write(LIST_VIEW_TEMPLATE.strip())
    with open(os.path.join(template_dir, "FormView.vue.j2"), "w") as f:
        f.write(FORM_VIEW_TEMPLATE.strip())
    with open(os.path.join(template_dir, "store.js.j2"), "w") as f:
        f.write(STORE_TEMPLATE.strip())
    with open(os.path.join(template_dir, "service.js.j2"), "w") as f:
        f.write(SERVICE_TEMPLATE.strip())
    with open(os.path.join(template_dir, "test.js.j2"), "w") as f:
        f.write(TEST_TEMPLATE.strip())
    with open(os.path.join(template_dir, "App.vue.j2"), "w") as f:
        f.write(APP_VUE_TEMPLATE.strip())
    with open(os.path.join(template_dir, "main.js.j2"), "w") as f:
        f.write(MAIN_JS_TEMPLATE.strip())
    with open(os.path.join(template_dir, "router_index.js.j2"), "w") as f:
        f.write(ROUTER_INDEX_TEMPLATE.strip())
    with open(os.path.join(template_dir, "package.json.j2"), "w") as f:
        f.write(PACKAGE_JSON_TEMPLATE.strip())
    with open(os.path.join(template_dir, "vite.config.js.j2"), "w") as f:
        f.write(VITE_CONFIG_TEMPLATE.strip())
    with open(os.path.join(template_dir, "index.html.j2"), "w") as f:
        f.write(INDEX_HTML_TEMPLATE.strip())
    with open(os.path.join(template_dir, "README.md.j2"), "w") as f:
        f.write(README_TEMPLATE.strip())
    print(f"Jinja2 frontend template files created in '{template_dir}'")


def main_vue_generator(
    tables_to_generate: List[Table],
    backend_api_url: str,
    root_table_names: List[str],
    force_overwrite: bool = False,
):
    create_template_files_frontend()
    generator = CRUDVueGenerator(
        tables=tables_to_generate,
        backend_api_url=backend_api_url,
        root_table_names=root_table_names,
    )
    generator.generate(output_dir="frontend", force_overwrite=force_overwrite)


# Example usage (for testing this generator independently)
if __name__ == "__main__":
    # Define dummy tables for testing
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
    root_tables = ["users"]  # Specify 'users' as a root table

    # Generate frontend files
    main_vue_generator(
        tables_to_generate, "http://localhost:8000", root_tables, force_overwrite=True
    )
