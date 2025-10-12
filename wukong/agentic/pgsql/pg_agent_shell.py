
import logging
import os
import json
import pathlib
import re
from typing import Callable, TypedDict, Annotated, List, Optional, Union
from functools import partial
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path
# LangChain/LangGraph imports
import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from prompt_toolkit import PromptSession
from prompt_toolkit import HTML
from prompt_toolkit import prompt as terminal_prompt
from prompt_toolkit.history import FileHistory

from .supervisor_agent import SupervisorAgent
from .text_to_sql_agent import TextToSQLAgent
from .pg_client import PostgreSQLClient
from wukong.llm.history_manager import LLMHistoryManager
from wukong.llm.llm_client import LLMClient
from ...wukong_config import wukong_config, WukongConfigManager
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
        

         

class PgAgentShell:
    def __init__(self, schema_context:Union[Path, str], dbclient:PostgreSQLClient, config:WukongConfigManager = None, reload:bool=False):   
        self.reload = reload  
        self.prompt_history = FileHistory(self._get_prompt_history_file())
        self.prompt_session = PromptSession(history=self.prompt_history)
        self.schema_context = schema_context        
        self.config = config if config is not None else wukong_config  
        self.console = Console()
        self.chat_history = LLMHistoryManager()
        model_id = self.config.get("text_to_sql.model_id", None)
        assert model_id is not None, "model_id must be specified in [text_to_sql] section of .wukong.toml"
         # initialize TextToSQLAgent        
        self.llm_client = self._get_llm_client()        
        self.text_to_sql_agent = TextToSQLAgent(
            database_schema = self.schema_context,
            model_id = model_id,
            dbclient = dbclient,
            llm_client = self.llm_client,
            reload_schema = self.reload,
            chat_history_manager = self.chat_history
        )
        print(f"Using model {model_id} for text to SQL")
        self.supervisor = SupervisorAgent(self.schema_context, model_id, self.llm_client, self.chat_history)
               
    
    def _get_llm_client(self) -> LLMClient:
        llm_config = self.config.get("llm", {})     
        base_url = llm_config.get("base_url", None)
        api_key = llm_config.get("api_key", None)
        llm_config = self.config.get("text_to_sql", {})  
           
        model_id = llm_config.get("model_id", None)    
        assert model_id is not None, "model_id must be specified in [text_to_sql] section of .wukong.toml"
        max_completion_tokens = llm_config.get("max_completion_tokens", None) 
        fallback_models = llm_config.get("fallback_models", [])
        history_limit = llm_config.get("history_limit", 100)               
        llm_client = LLMClient(
            model_id=model_id,
            base_url=base_url,
            api_key=api_key,
            max_completion_tokens=max_completion_tokens,
            fallback_models=fallback_models,
            history_manager=self.chat_history,
            history_limit=history_limit,
            streaming_handler=None
        )
        return llm_client
    
    
    def _get_prompt_history_file(self) -> Path:
        wukong_hist = Path.home() / ".wukong/.wukong_prompt_history"
        if wukong_hist.exists() is False:
            wukong_hist.parent.mkdir(exist_ok=True)
            wukong_hist.write_text("")            
        return wukong_hist.resolve()
    
    def display_welcome(self):
        """Display welcome message and instructions"""
        welcome_text = """Welcome to the interactive Wukong shell!
### Commands:
- Type your prompt and press Enter twice to submit
- Type 'exit' or 'quit' or 'bye' to leave
- Type 'clear' to clear CLI console screen
- Type 'clear history', 'save history', 'show history' to view, save and clear hsitory
- Press Ctrl+C to cancel current input

### Multi-line Input:
Enter your prompt. Press Enter twice (empty line) to submit.
        """
        self.console.print(Markdown(welcome_text))
        
    def get_multiline_input(self) -> Optional[str]:
        """Get multi-line input from user"""
        self.console.print("\n[bold cyan]Enter your prompt (double Enter to submit):[/bold cyan]")
        lines = []
        
        try:
            line_pos = 0
            while True:
                line_pos += 1
                if line_pos ==1:                    
                    line = self.prompt_session.prompt(HTML("<ansiyellow>[You]&gt;&gt;&gt; </ansiyellow>"))
                else:
                    line = self.prompt_session.prompt(HTML("<ansiyellow>... </ansiyellow>"))
                
                if len(lines)==1 and lines[0].strip() in ["quit", "exit", "bye", "\\q"] and line == "":
                    break                
                elif line == "" and lines and lines[-1] == "":
                    lines.pop()  # Remove the last empty line
                    break
                lines.append(line)                
                
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Input cancelled[/yellow]")
            return None
            
        prompt = "\n".join(lines).strip()
        return prompt if prompt else None
    
    
    def _show_history(self):
        hists = self.llm.chat_history.get_chat_history(40)
        for hist in hists:
            if hist.get("role") == "user":
                self.console.print(hist.get("content"))
    
    
    def process_command(self, command: str) -> bool:
        """Process special commands"""
        command_lower = command.lower().strip()
        
        if command_lower in ['exit', 'quit', 'q', "bye"]:
            self.console.print("[bold red]Goodbye![/bold red]")
            return False
            
        if command_lower == 'clear':            
            os.system('clear' if os.name == 'posix' else 'cls')
            self.display_welcome()
            return True        
        
        if re.search(r'^clear\s*history$', command_lower) or re.search(r'new(\s*chat)?$', command_lower):
            self.llm.chat_history.clear_history()            
            return True
        
        if re.search(r'^save\s*history$', command_lower):
            self.llm.chat_history.save_history()            
            return True
        
        if re.search(r'^show\s*history$', command_lower):
            self._show_history() 
            return True
                    
        return None    
    
    @staticmethod   
    def dict_list_to_markdown_table(data):
        """
        Convert a list of dictionaries to a markdown table format.
        
        Args:
            data (list): List of dictionaries with consistent keys
            
        Returns:
            str: Markdown formatted table string
        """
        if not data:
            return "No data available"
        
        # Get headers from the first dictionary
        headers = list(data[0].keys())
        
        # Create header row
        header_row = "| " + " | ".join(str(h) for h in headers) + " |"
        
        # Create separator row
        separator_row = "| " + " | ".join("---" for _ in headers) + " |"
        
        # Create data rows
        data_rows = []
        for item in data:
            row = "| " + " | ".join(str(item.get(h, "")) for h in headers) + " |"
            data_rows.append(row)
        
        # Combine all rows
        markdown_table = "\n".join([header_row, separator_row] + data_rows)
        
        return markdown_table    
        
    def run(self):
            """Main loop for the interactive shell"""
            self.display_welcome()
            while True:
                try:
                    # Get user input
                    user_input = self.get_multiline_input()
                    
                    if user_input is None:
                        continue
                        
                    # Check for special commands
                    command_result = self.process_command(user_input)
                    if command_result is not None:
                        if not command_result:
                            break
                        continue
                        
                    # Call LLM API
                    self.console.print("[green][Asisstant]: [/green]", end="")                    
                    if self.supervisor.review_query(user_input) == "SQL_QUERY": 
                        response = self.text_to_sql_agent.generate_and_execute_sql(user_input)
                        
                        if not response:                    
                            self.console.print("[red]No response received[/red]")
                            continue
                        else:
                            
                            if response.get("success"):
                                resp_str = self.dict_list_to_markdown_table(response.get("data", []))
                                self.chat_history.add_user_message(user_input)
                                self.chat_history.add_assistant_message(resp_str)
                                self.console.print(Panel(Markdown(resp_str), title="Query Result", subtitle=f"Rows: {response.get('row_count', 0)}"))
                            else: 
                                resp_str = response.get("error", "Unknown error") 
                                self.chat_history.add_user_message(user_input)
                                self.chat_history.add_assistant_message(resp_str)                                       
                                self.console.print(Panel(Markdown(resp_str), title="Error Response"))
                    else:
                        response_text = ""
                        for chunk in self.llm_client.invoke_model_stream(prompt=user_input):
                            print(chunk, end='', flush=True)
                            response_text += chunk
                        print("\n")
                        response_text = response_text.split("</think>")[-1].strip()
                        self.chat_history.add_user_message(user_input)
                        self.chat_history.add_assistant_message(response_text)                       
                        self.console.print(Panel(Markdown(response_text), title="General Chat Response"))
                        
                        
                except KeyboardInterrupt:
                    self.console.print("\n[yellow]Use 'exit' or 'quit' to leave the shell[/yellow]")
                except Exception as e:
                    logger.exception("An error occurred", e)
                    self.console.print(f"[red]Error: {str(e)}[/red]")

PG_CLIENT_PARAMS = [
    "database_url", "host", "port", "database", "user", "password", "max_conn"
]

def get_pg_config(section: str) -> dict:    
    dbprop = wukong_config.get(section)
    if not dbprop:
        raise ValueError(f"{section} is not configured in .wukong.toml")
    pgprops = {k: v for k, v in dbprop.items() if k in PG_CLIENT_PARAMS}
    if 'url' in dbprop:
        database_url = dbprop['url']        
        pgprops["database_url"] = database_url
    return pgprops

@click.command
@click.option("--database", "-d", type=str, default="database", help="database configuration section name in .kara_code.env.toml") 
@click.option("--schema-file", "-s", type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=pathlib.Path), help="Path to schema file for text to SQL", required=True)  
@click.option("--reload", "-r",  is_flag=True, type=bool, default=False, help="Reload schema from file every time")  
def pg_agent_shell(database: str, schema_file:pathlib.Path, reload:bool):
    """start an interactive LLM GenAI shell"""
    dbprop = get_pg_config(database)   
    with PostgreSQLClient(**dbprop) as dbclient:   
        shell = PgAgentShell(schema_file, dbclient, wukong_config, reload)
        shell.run()
       

if __name__ == "__main__":
    # Example 1: Save a file, then load it back in the same session
    # shell = AgenticShell()    
    # shell.run()   
    pg_agent_shell()