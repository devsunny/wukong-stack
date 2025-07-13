import click
import subprocess
# from .utils import update_pyproject, update_requirements


@click.command()
@click.argument("package")
def add_dependency(package):
    subprocess.run(["pip", "install", package])
    # update_pyproject(package)
    # update_requirements(package)
    