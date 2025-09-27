FILENAME_PROMPT = """act as a filename generator. Given a file content, generate a concise and descriptive filename for it. 
1. The filename should be in lowercase, use underscore to separate words, and have an appropriate file extension based on the content. 
2. Avoid using special characters or spaces in the filename. 
3. Only provide the filename without any additional text or explanation.

**file content**
\n\n{file_content}\n
"""
