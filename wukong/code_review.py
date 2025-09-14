import click
from wukong.llmclient import LLMClient
from wukong.prompts.code_review import (
    CODE_REVIEW_PROMPT,
    CODE_EXPLANATION_PROMPT,
    CODE_REFACTOR_PROMPT,
)
from wukong.prompts.unittest import UNITTEST_PROMPT
from wukong.source_code_utils import (
    read_source_file_or_directory,
    markdown_code_block_reader,
    write_code_to_files,
)


@click.command()
@click.argument("source_code", type=click.Path(exists=True))
def review_code(source_code):
    """Review the source code file or files in the given directory."""
    while not source_code or source_code.strip() in ["\\q", "\\quit"]:
        source_code = click.prompt(
            "Please enter the path to the source code file or directory (or \\q to quit)",
        )
    if source_code.strip() in ["\\q", "\\quit"]:
        return
    source = read_source_file_or_directory(source_code)
    llm_client = LLMClient()
    prompt = CODE_REVIEW_PROMPT + source
    for chunk in llm_client.invoke_llm_stream(prompt):
        print(chunk, end="", flush=True)
    # Call the review_source_code function from code_review module


@click.command()
@click.argument("source_code", type=click.Path(exists=True))
def explain_code(source_code):
    """Review the source code file or files in the given directory."""
    while not source_code or source_code.strip() in ["\\q", "\\quit"]:
        source_code = click.prompt(
            "Please enter the path to the source code file or directory (or \\q to quit)",
        )
    if source_code.strip() in ["\\q", "\\quit"]:
        return
    source = read_source_file_or_directory(source_code)
    llm_client = LLMClient()
    prompt = CODE_EXPLANATION_PROMPT + source
    for chunk in llm_client.invoke_llm_stream(prompt):
        print(chunk, end="", flush=True)
    # Call the review_source_code function from code_review module


@click.command()
@click.argument("source_code", type=click.Path(exists=True))
def refactor_code(source_code):
    """Review the source code file or files in the given directory."""
    while not source_code or source_code.strip() in ["\\q", "\\quit"]:
        source_code = click.prompt(
            "Please enter the path to the source code file or directory (or \\q to quit)",
        )
    if source_code.strip() in ["\\q", "\\quit"]:
        return
    source = read_source_file_or_directory(source_code)
    llm_client = LLMClient()
    prompt = CODE_REFACTOR_PROMPT.format(source_code=source)

    resp_text = ""
    for chunk in llm_client.invoke_llm_stream(prompt):
        resp_text += chunk
        print(chunk, end="", flush=True)
    sources = markdown_code_block_reader(resp_text)
    write_code_to_files(sources)


@click.command()
@click.argument("source_code", type=click.Path(exists=True))
def create_unit_tests(source_code):
    """Review the source code file or files in the given directory."""
    while not source_code or source_code.strip() in ["\\q", "\\quit"]:
        source_code = click.prompt(
            "Please enter the path to the source code file or directory (or \\q to quit)",
        )
    if source_code.strip() in ["\\q", "\\quit"]:
        return
    source = read_source_file_or_directory(source_code)
    llm_client = LLMClient()
    prompt = UNITTEST_PROMPT.format(source_code=source)

    resp_text = ""
    for chunk in llm_client.invoke_llm_stream(prompt):
        resp_text += chunk
        print(chunk, end="", flush=True)
    sources = markdown_code_block_reader(resp_text)
    # write_code_to_files(sources)
