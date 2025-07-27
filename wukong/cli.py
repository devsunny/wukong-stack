import click
from .init import init_project
from .database import database
from .code import crud


@click.group()
def cli():
    """Wukong Stack CLI Tool"""
    pass


cli.add_command(init_project, "init")
cli.add_command(database, "database")
cli.add_command(crud, "crud")


if __name__ == "__main__":
    cli()
