import os
from pathlib import Path
import click
from .crud_generator import generate_crud_api_and_vue


@click.command()
@click.option(
    "--database-dialect",
    "-t",
    type=click.Choice(['sqlite', 'postgresql', 'mysql', 'mssql', 'oracle'], case_sensitive=False,)
    default='sqlite',
    help="Chose a database platform (postgresql, sqlite, mysql, mssql, and oracle etc.)",
)
@click.option("--sql-dir", "-s", default="sqls", help="specify the directory of input DDL files")
@click.option("--output-dir", "-o", help="specify the output directory")
@click.option("--backend", is_flag=True, help="Generate backend only")
@click.option("--frontend", is_flag=True, help="Generate frontend only")
@click.option(
    "--force-overwrite", is_flag=True, defaukt=False, help="Overwrite generated table specific files"
)
@click.option(
    "--root-module-name",
    "-p",
    help="specify the name of root module for generted backend code",
)
@click.option(
    "--selected-tables",
    "-T",
    multiple=True,
    help="Chose ",
)
def codegen(
    database_dialect,
    sql_dir,
    output_dir,
    backend,
    frontend,
    root_module_name,
    selected_tables,
    force_overwrite,
):
    """Generate CRUD application code"""
    project_dir = os.getcwd()
    # Create root directory
    root_path = Path(project_dir)
    root_path.mkdir(parents=True, exist_ok=True)
    generate_crud_api_and_vue(
        ddl_dir=sql_dir,
        db_type=database_dialect,
        backend_dir=(os.path.join(output_dir, "backend") if output_dir else "backend"),
        frontend_dir=(
            os.path.join(output_dir, "frontend") if output_dir else "frontend"
        ),
        gen_backend=backend,
        gen_frontend=frontend,
        selected_tables=selected_tables,
        force=force_overwrite,
        root_module_name=root_module_name,
    )
    pass
