import click
from wukong.source_code_utils import (
    read_source_file_or_directory,
    markdown_code_block_reader,
    write_code_to_files,
)
from .prompts import UNITTEST_PROMPT
from wukong.llm.utils import create_llm_client

@click.command()
@click.argument("source_code", type=click.Path(exists=True))
def create_unit_tests(source_code):
    """Generate unit tests for file or files in the given directory."""
    while not source_code or source_code.strip() in ["\\q", "\\quit"]:
        source_code = click.prompt(
            "Please enter the path to the source code file or directory (or \\q to quit)",
        )
    if source_code.strip() in ["\\q", "\\quit"]:
        return
    source = read_source_file_or_directory(source_code)
    llm_client = create_llm_client()
    prompt = UNITTEST_PROMPT.format(source_code=source)
    resp_text = llm_client.invoke_model_stream(prompt, 
                                               include_history=False, 
                                               streaming_handler=lambda x: print(x, end="", flush=True))
    
    print(resp_text)
    
    sources = markdown_code_block_reader(resp_text)
    write_code_to_files(sources)