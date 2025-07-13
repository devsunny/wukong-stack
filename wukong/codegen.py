import click
import os


@click.command()
@click.option("--backend-only", is_flag=True, help="Generate backend only")
@click.option("--frontend-only", is_flag=True, help="Generate frontend only")
@click.option("--with-oauth", is_flag=True, help="Add OAuth2 authentication")
def codegen(backend_only, frontend_only, with_oauth):
    project_dir = os.getcwd()
    pass