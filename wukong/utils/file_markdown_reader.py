import os
import re
from io import StringIO
from pathlib import Path
from typing import Callable, Tuple
import click

LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".html": "html",
    ".css": "css",
    ".java": "java",
    ".cpp": "cpp",
    ".c": "c",
    ".sh": "bash",
    ".md": "markdown",
    ".txt": "text",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".xml": "xml",
    ".sql": "sql",
    ".rb": "ruby",
    ".php": "php",
    ".go": "go",
    ".rs": "rust",
}


def read_files_to_markdown(paths, include_hidden=False):
    """
    Read files from a list of file or folder paths and concatenate them in markdown format.

    Args:
        paths (list): List of file or folder paths to read
        include_hidden (bool): Whether to include hidden files/folders (default: False)

    Returns:
        str: Markdown formatted content with each file in its own code block
    """
    result = []

    for path_str in paths:
        path = Path(path_str)

        # Skip if path doesn't exist
        if not path.exists():
            continue

        # Check if hidden files/folders should be included
        if not include_hidden:
            # Check if current path is hidden (starts with .)
            if any(part.startswith(".") for part in path.parts):
                continue

        # If it's a file, read directly
        if path.is_file():
            content = read_single_file(path)
            result.append(content)

        # If it's a directory, recursively process files
        elif path.is_dir():
            # Get all files in the directory (and subdirectories if needed)
            for file_path in path.rglob("*"):
                # Skip directories and hidden files/folders
                if not file_path.is_file() or (
                    not include_hidden
                    and any(part.startswith(".") for part in file_path.parts)
                ):
                    continue

                content = read_single_file(file_path)
                result.append(content)

    return "\n".join(result)


def read_single_file(file_path):
    """
    Read a single file and format it as markdown.

    Args:
        file_path (Path): Path to the file

    Returns:
        str: Markdown formatted content
    """
    try:
        # Read file content
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Determine language for code block based on file extension
        _, ext = os.path.splitext(file_path)
        lang = LANGUAGE_MAP.get(ext, "text")

        # Format the output
        filepath = str(file_path)

        return f"""### Filename: {filepath}
```{lang}
{content}
```
"""
    except Exception as e:
        # If there's an error reading the file, include an error message
        return f"""### Filename: {file_path}
```
Error reading file: {str(e)}
```
"""


def save_code_blocks_auto(results: Tuple[str, str], base_dir=Path.cwd()):
    """
    Save code blocks with auto-numbering (no prompts).
    Args:
        results (list): List of tuples containing (filename, content)
        base_dir (str): Base directory to save files
    Returns:
        list: List of tuples containing (file_path, content)
    """

    for filename_match, code_content in results:
        filename = filename_match.strip()

        # Clean up the filename (remove any trailing newlines or spaces)
        filename = filename.rstrip("\n\r ")

        if not filename:
            continue

        # Full path
        full_path = os.path.join(base_dir, filename)

        # Create directory structure if needed
        Path(full_path).parent.mkdir(parents=True, exist_ok=True)

        # Generate numbered version automatically
        final_path = generate_numbered_filename(full_path)

        # Write the content to file
        try:
            with open(final_path, "w", encoding="utf-8") as f:
                f.write(code_content.strip())

            results.append((final_path, code_content.strip()))
            print(f"Saved: {final_path}")

        except Exception as e:
            print(f"Error saving file {full_path}: {e}")

    return results


def extract_unnamed_markdown_code_blocks(
    markdown_output, include_fences=False, filename_generator: Callable = None
):
    """
    Extract unnamed code blocks from LLM markdown output.

    Args:
        markdown_output (str): The markdown output from LLM
        include_fences (bool): Whether to include the code fences in the output (default: False)
    Returns:
        list: List of code block contents
    """

    results = []
    code_block = []
    in_code_block = False
    nested_blocks = 0
    for mdline in StringIO(markdown_output):
        line = mdline.strip()
        if re.search(r"^```[a-zA-Z0-9]+$", line) and in_code_block is False:
            if nested_blocks > 0:
                code_block.append(mdline)
            else:
                if include_fences:
                    code_block.append(mdline)
                in_code_block = True
            nested_blocks += 1

        elif re.search(r"^```$", line) and in_code_block:
            nested_blocks -= 1
            if nested_blocks == 0:
                if include_fences:
                    code_block.append(mdline)
                in_code_block = False
                if code_block:
                    results.append("\n".join(code_block).strip())
                code_block = []
            else:
                code_block.append(mdline)
        elif in_code_block:
            code_block.append(mdline)

    for code_block in results:
        if filename_generator:
            filename = filename_generator(code_block)
            results.append((filename, code_block))
        else:
            results.append((None, code_block))
    return results


def extract_markdown_code_blocks(markdown_output):
    """
    Extract code blocks from LLM markdown output.

    Args:
        markdown_output (str): The markdown output from LLM
    Returns:
        list: List of tuples containing (filename, content)
    """

    results = []
    filename = None
    code_block = []
    in_code_block = False
    nested_blocks = 0
    for mdline in StringIO(markdown_output):
        line = mdline.strip()
        if line.startswith("### Filename:"):
            filename = line.replace("### Filename:", "").strip()
            code_block = []
            in_code_block = False
        elif (
            re.search(r"^```[a-zA-Z0-9]+$", line)
            and in_code_block is False
            and filename is not None
        ):
            if nested_blocks > 0:
                code_block.append(mdline)
            else:
                in_code_block = True
            nested_blocks += 1

        elif re.search(r"^```$", line) and in_code_block:
            nested_blocks -= 1
            if nested_blocks == 0:
                in_code_block = False
                if filename and code_block:
                    results.append((filename, "\n".join(code_block).strip()))
                filename = None
                code_block = []
            else:
                code_block.append(mdline)
        elif in_code_block:
            code_block.append(mdline)
    return results


def extract_and_save_code_blocks(markdown_output, base_dir=Path.cwd()):
    """
    Extract code blocks from LLM markdown output and save them as files.

    Args:
        markdown_output (str): The markdown output from LLM
        base_dir (str): Base directory to save files

    Returns:
        list: List of tuples containing (file_path, content)
    """

    results = []

    for filename_match, code_content in extract_markdown_code_blocks(markdown_output):
        filename = filename_match.strip()

        # Clean up the filename (remove any trailing newlines or spaces)
        filename = filename.rstrip("\n\r ")

        if not filename:
            continue

        # Full path
        full_path = os.path.join(base_dir, filename)

        # Create directory structure if needed
        Path(full_path).parent.mkdir(parents=True, exist_ok=True)

        # Handle file overwrite confirmation or numbering
        final_path = handle_file_overwrite(full_path)

        # Write the content to file
        try:
            with open(final_path, "w", encoding="utf-8") as f:
                f.write(code_content.strip())

            results.append((final_path, code_content.strip()))
            print(f"Saved: {final_path}")

        except Exception as e:
            print(f"Error saving file {full_path}: {e}")

    return results


def handle_file_overwrite(file_path):
    """
    Handle file overwrite by either confirming or adding sequence number.

    Args:
        file_path (str): The target file path

    Returns:
        str: Final file path to use
    """
    if not os.path.exists(file_path):
        return file_path

    # File exists, ask for confirmation or generate numbered version
    while True:
        user_input = (
            click.prompt(
                f"File '{file_path}' already exists. Overwrite? (y/n) [default: n]: "
            )
            .strip()
            .lower()
        )

        if user_input in ["y", "yes"]:
            return file_path
        elif user_input in ["n", "no", ""]:
            # Generate numbered version
            base_name, ext = os.path.splitext(file_path)
            counter = 1

            while True:
                new_filename = f"{base_name}_{counter}{ext}"
                if not os.path.exists(new_filename):
                    return new_filename
                counter += 1
        else:
            click.echo("Please enter 'y' for yes or 'n' for no.")


# Alternative function that doesn't prompt user and always generates numbered versions
def extract_and_save_code_blocks_auto(markdown_output, base_dir=Path.cwd()):
    """
    Extract code blocks from LLM markdown output with auto-numbering (no prompts).

    Args:
        markdown_output (str): The markdown output from LLM
        base_dir (str): Base directory to save files

    Returns:
        list: List of tuples containing (file_path, content)
    """

    results = extract_markdown_code_blocks(markdown_output)
    results = save_code_blocks_auto(results, base_dir)
    return results


def generate_numbered_filename(file_path):
    """
    Generate a numbered filename if the original exists.

    Args:
        file_path (str): The target file path

    Returns:
        str: Final file path to use
    """
    if not os.path.exists(file_path):
        return file_path

    base_name, ext = os.path.splitext(file_path)
    counter = 1

    while True:
        new_filename = f"{base_name}_{counter:03d}{ext}"
        if not os.path.exists(new_filename):
            return new_filename
        counter += 1
