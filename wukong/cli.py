import click
from wukong.project_init import init_project
from wukong.project_create import create_project
from wukong.shell import shell
from wukong.code_review import (
    review_code,
    explain_code,
    refactor_code,
    create_unit_tests,
)  # Import the review_code function


@click.group()
def cli():
    """
    Razor-sharp AI wizard weaving code with unparalleled intellect!
    
    \b
          __
     w  c(..)o   (
      \\__(-)    __)
          /\\   (
         /(_)___)
         w /|
          | \\
         m  m
    Wukong, the legendary Monkey King was born from a magical stone 
    egg on the Mountain of Flowers and Fruit. I've got all the magic 
    you need for your coding journey!
    """
    pass


cli.add_command(init_project, "init")
cli.add_command(create_project, "create")
cli.add_command(review_code, "review")  # Add the review_code command
cli.add_command(explain_code, "explain")  # Add the explain_code command
cli.add_command(refactor_code, "refactor")  # Add the refactor_code command
cli.add_command(create_unit_tests, "unittest")  # Add the create_unit_tests command
cli.add_command(shell, "shell")  # Add the shell command


if __name__ == "__main__":
    cli()
