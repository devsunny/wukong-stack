import os
from .crud_api_generator import CRUDApiGenerator
from .crud_vue_generator import CRUDVueGenerator
from pgsql_parser import SQLParser


def generate_crud_api_and_vue(
    ddl_dir: str = "ddls",
    db_type: str = "postgresql",
    backend_dir="backend",
    frontend_dir="frontend",
    gen_backend=True,
    gen_frontend=True,
):
    """
    Generate CRUD API and Vue.js frontend files based on the provided table definitions.

    :param tables: List of Table objects defining the database schema.
    :param db_type: Type of the database (e.g., 'postgresql', 'mysql').
    """
    tables = []
    sqlparser = SQLParser()
    print(f"looking at DDL dir: {ddl_dir}")
    for file in os.listdir(ddl_dir):
        print
        if file.endswith(".sql") or file.endswith(".ddl"):
            sql_file_path = os.path.join(ddl_dir, file)
            print(f"Parsing SQL file: {sql_file_path}")
            with open(sql_file_path, "rt") as f:
                sql_script = f.read()
                ftables = sqlparser.parse_script(sql_script)
                if ftables:
                    tables.extend(ftables)
                    print(f"Parsed tables: {[table.name for table in tables]}")
    if len(tables) == 0:
        print("No tables found in the provided DDL files.")
        return

    if gen_backend is True:
        # 1. Instantiate the backend generator
        backend_gen = CRUDApiGenerator(tables=tables, db_type=db_type)
        # 2. Generate the backend files
        backend_gen.generate(backend_dir)
        print("CRUD API files generated successfully at:", backend_dir)
    if gen_frontend is True:
        # 3. Instantiate the frontend generator
        frontend_gen = CRUDVueGenerator(tables=tables)
        # 4. Generate the Vue.js frontend files
        frontend_gen.generate(frontend_dir)
        print("CRUD API and Vue.js frontend files generated successfully.")
