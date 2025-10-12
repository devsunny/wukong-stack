
import json
import logging
from pathlib import Path
from typing import Union
from wukong.llm.history_manager import LLMHistoryManager
from wukong.llm.llm_client import LLMClient

logger = logging.getLogger(__name__)


class SupervisorAgent:
    def __init__(self, 
            schema_context:Union[Path, str],
            llm_model:str,   
            llm_client :LLMClient ,
            chat_history_manager:LLMHistoryManager 
            ):
        
        self.llm_model = llm_model
        self.llm_client = llm_client
        self.chat_history_manager = chat_history_manager
        self.max_retries = 3
        self.database_schema = schema_context.read_text() if isinstance(schema_context, Path) else schema_context
        
    
    def review_query(self, user_question:str) -> str:
        prompt = f"""You are a system analyst. Your task is to review the the user's question to determine if it is asking for querying a database. or it is asking for some other information.
        
        if the question is asking for querying the database schema defined below, output "SQL_QUERY".
        if the question is asking for some other information, output "GENERAL_INFO".        
        
        ## Here is the database schema:
        {self.database_schema}
        
        ## USER QUESTION:
        <!user_question!>
        {user_question}
        </!user_question!>
        
        ## OUTPUT FORMAT: json
        
        If the question is asking for querying a database, output "SQL_QUERY".
        If the question is asking for some other information, output "GENERAL_INFO".
        
        ## EXAMPLES:
        
        Question: "show me all tables?"
        Output: 
        {{
            "type": "SQL_QUERY"
        }}
        
        Question: "Who is the president of the United States?"
        Output:         
        {{
            "type": "GENERAL_INFO"      
        }}
        
        Question: "Can you reformat the query results ...?"
        Output:         
        {{
            "type": "GENERAL_INFO"      
        }}
        
        important note: do not include any explanation or extra information, only output the json object as specified.        
        """
        print("Reviewing user question to determine query type...", self.llm_model)
        for attempt in range(1, self.max_retries + 1):
            response = ""
            stream = self.llm_client.invoke_model(
                model_id=self.llm_model,
                prompt=prompt,
                streaming=True
            )
            
            if stream is None:
                return "SQL_QUERY"
            
            for chunk in stream:
                response += chunk
                print(chunk, end='', flush=True)
            print("\n")     
            try:
                response = response.split("</think>")[-1].strip()
                logger.info(f"LLM Response: {response}")
                response_json = json.loads(response)
                if "type" in response_json:
                    return response_json["type"]
                else:
                    print(f"Attempt {attempt}: 'type' field not found in response. Retrying...")
            except json.JSONDecodeError as e:
                print(f"Attempt {attempt}: JSON decode error: {e}. Retrying...")
        
        return "GENERAL_INFO"
        