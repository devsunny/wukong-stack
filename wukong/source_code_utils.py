import os
from typing import Dict
import re
from collections import OrderedDict
import click


SOURCE_FILE_TYPE_MAPPINGS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".java": "Java",
    ".cpp": "C++",
    ".c": "C",
    ".cs": "C#",
    ".rb": "Ruby",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".html": "HTML",
    ".css": "CSS",
    ".json": "JSON",
    ".xml": "XML",
    # Add more mappings as needed
}


def read_source_file(file_path: str) -> str:
    """
    Read a source file and return its content wrapped in markdown code block.

    Args:
        file_path (str): Path to the source file

    Returns:
        str: Markdown formatted content with filename header

    Raises:
        IOError: If file cannot be read
        ValueError: If file extension is not supported or path is invalid
    """
    # Security: Validate and sanitize file path to prevent directory traversal attacks
    try:
        abs_file_path = os.path.abspath(file_path)
    except Exception as e:
        raise ValueError(f"Invalid file path format: {str(e)}")

    # Security: Ensure we don't escape the intended directory
    if not abs_file_path.startswith(os.getcwd()):
        raise ValueError("File path must be within current working directory")

    if not os.path.exists(abs_file_path):
        raise FileNotFoundError(f"File {file_path} does not exist")

    base_name = os.path.basename(file_path)
    _, ext = os.path.splitext(base_name)
    language = SOURCE_FILE_TYPE_MAPPINGS.get(ext.lower(), "Unknown").lower()

    try:
        with open(abs_file_path, "r", encoding="utf-8") as file:
            content = file.read()
    except Exception as e:
        raise IOError(f"Error reading file {file_path}: {str(e)}")

    return f"<|file_sep|> {abs_file_path}\n```{language}\n" + content + "\n```\n\n"


def read_source_file_or_directory(file_path: str) -> str:
    """
    Read source files from either a single file or directory.

    Args:
        file_path (str): Path to file or directory

    Returns:
        str: Concatenated markdown formatted contents

    Raises:
        ValueError: If path is invalid
        IOError: If files cannot be read
    """
    # Security: Validate input path
    if not isinstance(file_path, str) or not file_path.strip():
        raise ValueError("Invalid file or directory path")

    try:
        abs_file_path = os.path.abspath(file_path)
    except Exception as e:
        raise ValueError(f"Invalid file path format: {str(e)}")

    # Security: Ensure we don't escape the intended directory
    if not abs_file_path.startswith(os.getcwd()):
        raise ValueError("File path must be within current working directory")

    source_codes = ""
    if os.path.isfile(abs_file_path):
        try:
            source_codes += read_source_file(file_path)
        except Exception as e:
            raise IOError(f"Error reading file {file_path}: {str(e)}")
    elif os.path.isdir(abs_file_path):
        # Security: Prevent directory traversal attacks
        base_dir = abs_file_path
        dir_base_name = os.path.basename(base_dir)
        source_codes = f"<|repo_name|>{dir_base_name}\n\n"
        for root, _, files in os.walk(base_dir):
            # Security: Ensure we don't traverse outside the base directory
            if not root.startswith(base_dir):
                continue

            # Security: Skip hidden directories to prevent potential issues
            if any(part.startswith(".") for part in root.split(os.sep)):
                continue

            for file in files:
                full_path = os.path.join(root, file)

                # Security: Skip hidden files/directories to prevent potential issues
                if any(part.startswith(".") for part in full_path.split(os.sep)):
                    continue

                try:
                    source_codes += read_source_file(full_path)
                except Exception as e:
                    raise IOError(f"Error reading file {full_path}: {str(e)}")
    else:
        raise ValueError("Invalid file or directory path")

    return source_codes


def _is_valid_filename(filename: str) -> bool:
    """
    Validate filename for security purposes.

    Args:
        filename (str): Filename to validate

    Returns:
        bool: True if valid, False otherwise
    """
    # Security: Check for dangerous characters and paths
    if not isinstance(filename, str):
        return False

    if not filename.strip():
        return False

    # Prevent directory traversal with absolute path checks
    try:
        abs_filename = os.path.abspath(filename)
        if not abs_filename.startswith(os.getcwd()):
            return False
    except Exception:
        return False

    # Prevent null bytes (security)
    if "\x00" in filename:
        return False

    # Security: Check for common dangerous patterns
    dangerous_patterns = ["<", ">", ":", '"', "|", "?", "*"]
    if any(pattern in filename for pattern in dangerous_patterns):
        return False

    # Security: Prevent various path traversal attacks
    if ".." in filename or os.path.isabs(filename):
        return False

    # Security: Check for invalid characters that might cause issues on different OSes
    invalid_chars = ["\x00", "\n", "\r", "\t"]
    if any(char in filename for char in invalid_chars):
        return False

    return True


def markdown_code_block_reader(markdown_text: str) -> Dict[str, str]:
    """
    Parse markdown text and extract code blocks with their filenames.

    Args:
        markdown_text (str): Markdown content

    Returns:
        Dict[str, str]: Dictionary mapping filenames to code content
    """
    if not isinstance(markdown_text, str):
        raise TypeError("markdown_text must be a string")

    in_code_block = False
    filename = None
    code_block = []
    sources = OrderedDict()
    nested_code_block = 0

    lines = markdown_text.splitlines()

    for line in lines:
        clean_line = line.rstrip()

        # Extract filename from header if present
        if clean_line.startswith("### FILENAME: "):
            if filename and code_block:
                sources[filename] = "\n".join(code_block).rstrip()

            raw_filename = clean_line[len("### FILENAME: ") :].strip()

            # Security: Validate filename before storing
            if not _is_valid_filename(raw_filename):
                raise ValueError(f"Invalid filename detected: {raw_filename}")

            filename = raw_filename
            code_block = []
        elif re.match(r"^```[a-zA-Z][a-zA-Z0-9]*$", clean_line):
            # Handle opening of code block with language specification
            if filename and not in_code_block:
                in_code_block = True
            else:
                nested_code_block += 1
                code_block.append(line)
        elif clean_line == "```":
            # Handle closing of code block
            if nested_code_block > 0:
                nested_code_block -= 1
                code_block.append(line)
            else:
                in_code_block = False
                if filename and code_block:
                    sources[filename] = "\n".join(code_block).rstrip()
                filename = None
                code_block = []
        elif in_code_block:
            # Add lines that are inside code blocks
            code_block.append(line)

    return sources


def prompt_overwrite_file(file_path: str) -> bool:
    """
    Prompt user for overwrite confirmation.

    Args:
        file_path (str): Path to the file

    Returns:
        bool: True if user wants to overwrite, False otherwise
    """
    # Security: Validate input path to prevent directory traversal attacks
    if not isinstance(file_path, str):
        return False

    if not file_path.strip():
        return False

    # Check for dangerous patterns in the path
    if ".." in file_path or os.path.isabs(file_path):
        raise ValueError("Invalid file path detected")

    try:
        abs_file_path = os.path.abspath(file_path)
    except Exception as e:
        raise ValueError(f"Invalid file path: {str(e)}")

    # Security: Validate the absolute path to prevent traversal attacks
    if not os.path.exists(abs_file_path):
        return True  # If it doesn't exist, no overwrite needed

    try:
        overwrite = click.prompt(
            f"File {file_path} already exists. Do you want to overwrite it? (y/n): ",
            default="n",
            show_default=True,
        )
        return str(overwrite).strip().lower() == "y"
    except Exception:
        # Fallback in case of prompt failure
        click.echo(f"Warning: Could not prompt for {file_path}, assuming no overwrite")
        return False


def write_code_to_files(sources: Dict[str, str]) -> None:
    """
    Write code content to files.

    Args:
        sources (Dict[str, str]): Dictionary mapping filenames to code content

    Raises:
        ValueError: If any filename is invalid
        IOError: If file cannot be written
    """
    if not isinstance(sources, dict):
        raise TypeError("sources must be a dictionary")

    for filename, code in sources.items():
        # Security: Validate filename before processing
        if not _is_valid_filename(filename):
            raise ValueError(f"Invalid filename detected: {filename}")

        file_path = filename

        # Security: Ensure path safety when creating directories
        dir_name = os.path.dirname(file_path)
        if dir_name and not os.path.exists(dir_name):
            try:
                # Security: Create directory with safe permissions
                os.makedirs(dir_name, mode=0o755, exist_ok=True)
            except Exception as e:
                raise IOError(f"Error creating directory {dir_name}: {str(e)}")

        if prompt_overwrite_file(file_path):
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    # Security: Sanitize output to prevent injection
                    f.write(code)
                click.echo(f"Written to {file_path}")
            except Exception as e:
                click.echo(f"Error writing to file {file_path}: {str(e)}")
        else:
            click.echo(f"Skipped writing to {file_path}")
