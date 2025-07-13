import click
from .init import init_project
from .codegen import codegen
from .add import add_dependency
from .version import increase_build, increase_minor, increase_major
from .oauth2 import enable_oauth2


@click.group()
def cli():
    """Wukong Stack CLI Tool"""
    pass


cli.add_command(init_project, "init")
cli.add_command(codegen, "codegen")
cli.add_command(add_dependency, "add")
cli.add_command(increase_build, "increase-build")
cli.add_command(increase_minor, "increase-minor")
cli.add_command(increase_major, "increase-major")
cli.add_command(enable_oauth2, "enable-oauth2")
