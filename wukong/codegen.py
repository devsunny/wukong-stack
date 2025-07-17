import os
from pathlib import Path
import click


@click.command()
@click.option("--backend-only", is_flag=True, help="Generate backend only")
@click.option("--frontend-only", is_flag=True, help="Generate frontend only")
@click.option("--with-oauth", is_flag=True, help="Add OAuth2 authentication")
def codegen(backend_only, frontend_only, with_oauth):
    """Generate CRUD application code"""
    project_dir = os.getcwd()
    # Create root directory
    root_path = Path(project_dir)
    root_path.mkdir(parents=True, exist_ok=True)

    pass
    