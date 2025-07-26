import click
from .commands.flask_project_init import create_flask_project_structure


@click.group()
def init_project():
    pass


@click.command
@click.option(
    "--output-dir",
    required=False,
    default=None,
    type=str,
    help="project base directory",
)
@click.option(
    "--flask-dir",
    required=False,
    default="backend",
    type=str,
    help="project base directory",
)
def init_flask(output_dir, flask_dir):
    create_flask_project_structure(
        project_base_dir=output_dir, flask_base_dir=flask_dir
    )
    pass


init_project.add_command(init_flask, "flask")
