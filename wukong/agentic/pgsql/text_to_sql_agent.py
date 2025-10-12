# agents/text_to_sql_agent.py
# Requires: openai

from pathlib import Path
from typing import Dict, Any, Optional
from openai import OpenAI
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

from .prompt_builder import SQLPromptBuilder
from .sql_execution_agent import SQLExecutorAgent
from .pg_client import PostgreSQLClient
from wukong.llm.history_manager import LLMHistoryManager
from wukong.llm.llm_client import LLMClient

MAX_SQL_RETRY_ATTEMPTS = 3

class TextToSQLAgent:
    def __init__(
        self,
        database_schema: str,
        model_id:str,
        dbclient:PostgreSQLClient,
        llm_client :LLMClient,   
        reload_schema:bool=False  ,
        chat_history_manager:LLMHistoryManager = None   
    ):      
        self.prompt_session = self._create_prompt_session()        
        self.prompt_builder = SQLPromptBuilder(database_schema, reload_schema)
        self.llm_client = llm_client
        self.executor_agent = SQLExecutorAgent(dbclient)
        self.chat_history_manager = chat_history_manager
        self.selected_model = model_id    
        self.max_retries = MAX_SQL_RETRY_ATTEMPTS   
        
        
    def _create_prompt_session(self) -> PromptSession:
        kara_code_hist = Path.home() / ".kara_code/.kara_prompt_history"
        if kara_code_hist.exists() is False:
            kara_code_hist.parent.mkdir(exist_ok=True)
            kara_code_hist.write_text("")
            
        self.prompt_history = FileHistory(kara_code_hist.resolve())
        return PromptSession(history=self.prompt_history)
    
          

    def _clean_sql(self, sql: str) -> str:        
        sql = sql.split("</think>")[-1].strip()  # in case LLM adds <think> tags
        sql = sql.strip()
        if sql.startswith("```sql"):
            sql = sql[6:]
        elif sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
        sql = sql.strip()
        if sql.endswith(";"):
            sql = sql[:-1]
        return sql

    def generate_and_execute_sql(self, user_query: str) -> Dict[str, Any]:        
        prompt = self.prompt_builder.build_initial_prompt(user_query)        
        for attempt in range(1, MAX_SQL_RETRY_ATTEMPTS + 1):
            sql_response = ""
            for chunk in self.llm_client.invoke_model_stream(prompt=prompt):
                sql_response += chunk
                print(chunk, end='', flush=True)
            print("\n")     
            sql = self._clean_sql(sql_response)
            
            result = self.executor_agent.execute_and_validate(sql)
            
            if result["success"]:
                return {
                    "success": True,
                    "query": user_query,
                    "sql": sql,
                    "data": result["data"],
                    "columns": result["columns"],
                    "row_count": result["row_count"],
                    "attempts": attempt
                }
            
            if attempt < MAX_SQL_RETRY_ATTEMPTS:
                feedback = self.executor_agent.get_feedback_for_llm(result)
                prompt = self.prompt_builder.build_fix_prompt(
                    user_query,
                    sql,
                    result["error"],
                    attempt + 1
                )
            else:
                return {
                    "success": False,
                    "query": user_query,
                    "sql": sql,
                    "error": result["error"],
                    "error_type": result["error_type"],
                    "attempts": attempt,
                    "message": "Maximum retry attempts reached"
                }
        
        return {
            "success": False,
            "query": user_query,
            "message": "Failed to generate valid SQL",
            "attempts": MAX_SQL_RETRY_ATTEMPTS
        }