import click
from .init import init_project


@click.group()
def cli():
    """Wukong Stack CLI Tool"""
    pass


cli.add_command(init_project, "init")


if __name__ == "__main__":
    cli()
