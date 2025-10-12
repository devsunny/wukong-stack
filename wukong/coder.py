import click
from wukong.llmclient import LLMClient
from wukong.utils.filename_utils import generate_filename
from wukong.utils.file_markdown_reader import (
    extract_and_save_code_blocks_auto,
    extract_unnamed_markdown_code_blocks,
    read_files_to_markdown,
    save_code_blocks_auto,
)


@click.command()
@click.option("--prompt", type=str, help="Prompt for the AI code assistant")
@click.option(
    "--prompt-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Path to the prompt file",
)
@click.option(
    "--save-llm-output",
    is_flag=True,
    help="Save raw LLM output to a file",
    default=False,
)
@click.option(
    "--extract-code",
    is_flag=True,
    help="Extract code blocks from LLM output and save to files",
    default=False,
)
@click.option(
    "--exclude",
    multiple=True,
    type=click.Path(exists=True, file_okay=True, dir_okay=True),
    help="Directories or files to exclude when reading source files",
    default=[],
)
@click.argument(
    "args", nargs=-1, type=click.Path(exists=True, file_okay=True, dir_okay=True)
)
def code_assitant(prompt, prompt_file, save_llm_output, extract_code, exclude, args):
    """
    AI Code Assistant CLI
    """
    final_prompt = ""
    if prompt:
        final_prompt = prompt

    if prompt_file:
        if final_prompt:
            final_prompt += "\n"
        with open(prompt_file, "r") as file:
            final_prompt += file.read()

    while not final_prompt:
        final_prompt = click.edit(
            "Enter prompt here. Save and close the editor to submit."
        )
        if final_prompt.strip() in ["exit", "quit", "q"]:
            click.echo("No prompt provided. Exiting.")
            return

    click.echo(f"Final prompt:\n{final_prompt}")
    if args:
        click.echo(f"Arguments: {list(args)}")
        source_files = read_files_to_markdown(args, exclude=exclude)
        final_prompt += "\n\n" + source_files

    llm_client = LLMClient()
    response_content = ""
    for chunk in llm_client.invoke_llm_stream(final_prompt, include_history=False):
        response_content += chunk
        print(chunk, end="", flush=True)
    print("\n")
    if save_llm_output:
        filename = generate_filename(response_content)
        with open(filename, "w") as f:
            f.write(response_content)
        click.echo(f"LLM output saved to {filename}")
    if extract_code:
        results = extract_and_save_code_blocks_auto(response_content)
        if results:
            click.echo("Extracted and saved the following files:")
            for file_path, _ in results:
                click.echo(f"- {file_path}")
        else:
            results = extract_unnamed_markdown_code_blocks(
                response_content, filename_generator=generate_filename
            )
            save_code_blocks_auto(results)
            if results:
                click.echo("Extracted and saved the following files:")
                for file_path, _ in results:
                    click.echo(f"- {file_path}")
            else:
                click.echo("No code blocks found to extract.")
