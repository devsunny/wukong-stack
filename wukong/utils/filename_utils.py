from wukong.llmclient import LLMClient
from wukong.prompts.filename import FILENAME_PROMPT


def generate_filename(file_content):
    """
    Generate a concise and descriptive filename based on the provided file content.

    Args:
        file_content (str): The content of the file for which to generate a filename.

    Returns:
        str: Generated filename.
    """
    prompt = FILENAME_PROMPT.format(file_content=file_content)
    llm_client = LLMClient()
    response = llm_client.invoke_llm(prompt, include_history=False)
    filename = response.strip().split("\n")[0]  # Get the first line as filename
    return filename
