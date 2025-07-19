import os
from atlas_pyproject_manager.crud_api_generator import CRUDApiGenerator
from atlas_pyproject_manager.crud_vue_generator import CRUDVueGenerator
from jinja2 import Environment, FileSystemLoader, select_autoescape
from .sqlparser import SQLParser
from .jinja2_template_render import Jinja2TemplateRender


def generate_crud_api_and_vue(
    ddl_dir: str = "ddls",
    db_type: str = "postgresql",
    backend_dir="backend",
    frontend_dir="frontend",
    gen_backend=True,
    gen_frontend=True,
    selected_tables=None,
    force: bool = False,
    root_module_name=None,
):
    """
    Generate CRUD API and Vue.js frontend files based on the provided table definitions.

    :param tables: List of Table objects defining the database schema.
    :param db_type: Type of the database (e.g., 'postgresql', 'mysql').
    """
    tables = []
    sqlparser = SQLParser()
    for file in os.listdir(ddl_dir):
        if file.endswith(".sql") or file.endswith(".ddl"):
            sql_file_path = os.path.join(ddl_dir, file)
            print(f"Parsing SQL file: {sql_file_path}")
            with open(sql_file_path, "rt") as f:
                sql_script = f.read()
                sqlparser.parse_script(sql_script)
                ftables = sqlparser.get_tables()
                if ftables:
                    tables.extend(ftables)
                    print(f"Parsed tables: {[table.name for table in tables]}")

    selected_tables = selected_tables or []
    selected_tables = [
        table.strip().upper() for table in selected_tables if table.strip()
    ]
    tables = [
        table
        for table in tables
        if not selected_tables or table.name.upper() in selected_tables
    ]
    if len(tables) == 0:
        print("No tables found in the provided DDL files.")
        return
    for table in tables:
        print(f"Table: {table.name}, Columns: {[col for col in table.columns]},")

    if gen_backend is True:
        # 1. Instantiate the backend generator
        backend_gen = CRUDApiGenerator(
            tables=tables,
            root_table_names=["connectors"],
            db_type=db_type,
            root_module_name=root_module_name,
        )
        # 2. Generate the backend files
        backend_gen.generate(backend_dir, force_overwrite=True),
        print("CRUD API files generated successfully at:", backend_dir)

    # if gen_frontend is True:
    #     # 3. Instantiate the frontend generator
    #     frontend_gen = CRUDVueGenerator(tables=tables)
    #     # 4. Generate the Vue.js frontend files
    #     frontend_gen.generate(frontend_dir, force_overwrite=force)
    #     print("CRUD API and Vue.js frontend files generated successfully.")

    # tplrender = Jinja2TemplateRender("templates")
    # tgt = backend_dir or frontend_dir
    # output_dir = os.path.dirname(tgt)
    # outfile = os.path.join(output_dir, "README.md")
    # global_context = {
    #     "gen_backend": gen_backend,
    #     "gen_frontend": gen_frontend,
    #     "db_type": db_type,
    # }

    # # tplrender.render_template(
    # #     "readme.md.j2", global_context, output_file=outfile, force_overwrite=force
    # # )
