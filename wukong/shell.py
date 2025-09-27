import re
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
        click.echo("Welcome to the Wukong interactive shell! Type 'exit' to quit; 'edit' for multi-line input; 'clear history' to clear conversation history; 'save history' to save conversation history.")
        while True:
            try:
                user_input = click.prompt("Wukong> ")
                if user_input.lower() in ["exit", "quit"]:
                    self.llm_client.save_history()
                    click.echo("Exiting Wukong shell. Goodbye!")
                    break
                elif user_input.lower() in ["clear", "cls"]:
                    click.clear()
                    click.echo(PROMPT)
                    continue    
                elif user_input.lower() in ["help", "?"]:
                    click.echo("Commands:\n - exit, quit: Exit the shell\n - clear, cls: Clear the screen\n - clear history: Clear conversation history\n - save history: Save conversation history\n - edit: Enter multi-line input mode")
                    continue    
                elif re.match(r"^clear\s+history$", user_input.strip(), re.IGNORECASE):
                    self.llm_client.clear_history()
                    click.echo("Conversation history cleared.")
                    continue
                elif re.match(r"^save\s+history$", user_input.strip(), re.IGNORECASE):
                    self.llm_client.save_history()
                    click.echo("Conversation history saved.")
                    continue   
                elif re.match(r"^show\s+history$", user_input.strip(), re.IGNORECASE):
                    self.llm_client.show_history()
                    continue
                elif user_input.strip() == "edit":
                    user_input = click.edit("\n# Enter your multi-line input above. Lines starting with '#' will be ignored.\n")
                    if user_input is None:
                        click.echo("No input provided.")
                        continue
                    user_input = "\n".join([line for line in user_input.splitlines() if not line.strip().startswith("#")])
                    if not user_input.strip():
                        click.echo("No valid input provided.")
                        continue                     
                
                if not user_input.strip():
                    continue
                
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
