import click
from wukong.llmclient import LLMClient

PROMPT = """
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


class WukongShell:
    def __init__(self):
        self.llm_client = LLMClient()

    def start(self):
        click.echo(PROMPT)
        click.echo("Welcome to the Wukong interactive shell! Type 'exit' to quit.")
        while True:
            try:
                user_input = click.prompt("Wukong> ")
                if user_input.lower() in ["exit", "quit"]:
                    click.echo("Exiting Wukong shell. Goodbye!")
                    break
                for resp in self.llm_client.invoke_llm_stream(user_input):
                    click.echo(resp, nl=False)

                click.echo()  # For a new line after the response
            except Exception as e:
                click.echo(f"Error: {e}")


@click.command()
def shell():
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
    WukongShell().start()
