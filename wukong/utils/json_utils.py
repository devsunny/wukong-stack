import json
import re
from typing import List, Optional
from io import StringIO

def extract_json_from_text(text: str) -> str:
    """
    Extracts the first JSON object found in the given text.

    Args:
        text (str): The input text containing JSON. It may contain other text before or after the JSON. The JSON may be enclosed in triple backticks (```). It may also be malformed with single quotes instead of double quotes.           
    Returns:
        str: The extracted JSON string, or an empty string if no JSON is found.
    """
    # Regex pattern to match JSON objects, optionally enclosed in triple backticks
    in_code_block = False    
    code_block_delimiter = "```"
    json_text  = ""
    if code_block_delimiter in text:
        for line in StringIO(text):            
            if in_code_block is False and line.strip().startswith(code_block_delimiter):
                in_code_block = True
            elif in_code_block and line.strip().endswith(code_block_delimiter):
                in_code_block = False
                break  # Stop after the first code block
            elif in_code_block:
                json_text += line
    else:
        
        start_index = text.find('{')
        end_index = text.rfind('}') + 1  # Include the closing brace
        while start_index != -1 and end_index != -1 and not is_valid_json(text[start_index:end_index]):
            # If the extracted text is not valid JSON, try to find the next '{' and '}' pair           
            end_index = text.rfind('}', 0, end_index - 1) + 1
        if start_index != -1 and end_index != -1 and end_index > start_index:
            json_text = text[start_index:end_index] 
        else:
            json_text = text
    
    return json_text.strip()  # Return empty string if no JSON found   

def is_valid_json(json_str: str) -> bool:
    """
    Checks if the given string is a valid JSON.

    Args:
        json_str (str): The input string to check.
    Returns:
        bool: True if the string is valid JSON, False otherwise.    
        
    """
    try:
        json.loads(json_str)
        return True
    except json.JSONDecodeError:
        return False
    
"""
```json
{
  "table_name": "employee",
  "table_description": "Stores employee information including personal details, job roles, employment status, and leave balances.",
  "example_user_queries": [
    {
      "user_query": "List all employees working as a Marketing Manager",
      "sql_template": "SELECT * FROM humanresources.employee WHERE jobtitle = '<job_title>'"
    },
    {
      "user_query": "Find employee details by national ID number",
      "sql_template": "SELECT * FROM humanresources.employee WHERE nationalidnumber = '<national_id>'"
    },
    {
      "user_query": "Show employees hired between specific dates",
      "sql_template": "SELECT * FROM humanresources.employee WHERE hiredate BETWEEN '<start_date>' AND '<end_date>'"
    },
    {
      "user_query": "Retrieve current employees with their job titles",
      "sql_template": "SELECT jobtitle, loginid FROM humanresources.employee WHERE currentflag = true"
    },
    {
      "user_query": "Get employee details with vacation hours greater than X",
      "sql_template": "SELECT * FROM humanresources.employee WHERE vacationhours > <threshold>"
    },
    {
      "user_query": "Find employees by marital status and gender",
      "sql_template": "SELECT * FROM humanresources(employee WHERE maritalstatus = '<marital_status>' AND gender = '<gender>'"
    }
  ]
}
```
"""