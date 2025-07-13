import os
from pathlib import Path
import click
from .utils import parser_ddls

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

    # Create directory structure
    directories = [       
        "backend/app/api/v1/endpoints",
        "backend/app/auth",
        "backend/app/models",
        "backend/app/schemas",       
        # "frontend/public",
        # "frontend/src/assets",
        # "frontend/src/components",
        # "frontend/src/views",
        # "frontend/src/router",
        # "frontend/src/store",
        # "frontend/src/services",
    ]
    # Create all directories
    for directory in directories:
        (root_path / directory).mkdir(parents=True, exist_ok=True)
    tables = parser_ddls(project_dir)
    