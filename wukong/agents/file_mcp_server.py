from fastmcp import FastMCP
import os

mcp = FastMCP("FileMCP Server")


@mcp.tool
def save_file(file_path: str, content: str) -> str:
    """
    Save the provided content to a file at the specified path.

    Args:
        file_path: The path to the file to save.
        content: The content to write to the file.

    Returns:
        A confirmation message.
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File successfully saved to {file_path}"
    except Exception as e:
        return f"Error saving file: {str(e)}"


@mcp.tool
def read_file(file_path: str) -> str:
    """
    Read the content of a programming source file from the specified path.

    Args:
        file_path: The path to the file to read.

    Returns:
        The content of the file.
    """
    try:
        if not os.path.exists(file_path):
            return f"Error: File not found at {file_path}"
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"


if __name__ == "__main__":
    mcp.run()
