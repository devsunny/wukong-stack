import getpass
from pathlib import Path
from typing import Any, Callable, List
from openai import OpenAI, OpenAIError, RateLimitError, BadRequestError
import httpx

from .history_manager import LLMHistoryManager


class LLMClient:
    
    def __init__(self, 
                 model_id:str,
                 base_url = None, 
                 api_key=None, 
                 max_completion_tokens:int=None,  
                 fallback_models=None,
                 history_manager:LLMHistoryManager = None,
                 history_limit:int = 100,
                 streaming_handler:Callable[[str], None]=None,
                 ):   
        self.base_url = base_url
        self.api_key = api_key or "llmclient"        
        self.max_completion_tokens = max_completion_tokens   
        self.model_id = model_id
        self.fallback_models = fallback_models if fallback_models is not None else []
        self.llm_models = [model_id] + self.fallback_models if self.fallback_models else [model_id]
        self.history_manager = history_manager 
        self.history_limit = history_limit
        self.streaming_handler = streaming_handler
        
    def _get_llm(self)->OpenAI:
        granular_timeout = httpx.Timeout(25.0, connect=5.0, read=180.0, write=5.0)        
        openai_params = {}
        if self.base_url is not None:
            openai_params["base_url"] = self.base_url        
        openai_params["api_key"] = self.api_key
        openai_params["timeout"] = granular_timeout
        llm = OpenAI(**openai_params)
        return llm        

    
    def get_messages_with_history(self, 
                     messages, 
                     history_manager:LLMHistoryManager = None)-> List[dict[str, Any]]:
        hist_man = history_manager if history_manager is not None else self.history_manager 
        hist_msgs = hist_man.get_chat_history(self.history_limit) if hist_man is not None else []        
        return hist_msgs + messages
    
    def invoke_model(self, prompt=None, 
                     messages = None, 
                     model_id:str = None,
                     max_tokens:int = 0, 
                     max_completion_tokens:int = 0, 
                     temperature=0.1,
                     system_prompt:str = None,
                     history_manager:LLMHistoryManager = None,
                     streaming:bool = False)->str:        
        llm = self._get_llm()        
        req_max_tokens = max(max_tokens, max_completion_tokens)
        if req_max_tokens == 0:
            req_max_tokens = None
        if self.max_completion_tokens and req_max_tokens and req_max_tokens > self.max_completion_tokens:
            req_max_tokens = self.max_completion_tokens        
          
        input_messages = messages if messages is not None else [{"role": "user", "content": prompt}]
        llm_messages = self.get_messages_with_history(input_messages, history_manager=history_manager)
        if system_prompt:
            llm_messages.insert(0, {"role": "system", "content": system_prompt})
        
        selected_model = model_id if model_id is not None else self.model_id
        models = [selected_model] + self.fallback_models if self.fallback_models else [selected_model]
        for model_id in models:
            try:                
                response = llm.chat.completions.create(        
                    model=model_id,  # or any other model you want to use
                    max_completion_tokens = req_max_tokens,
                    messages=llm_messages,
                    stream=streaming                    
                )  
                response_txt = ""              
                if streaming:                    
                    for chunk in response:                        
                        finish_reason = chunk.choices[0].finish_reason
                        resp_chunk = chunk.choices[0].delta.content
                        if resp_chunk is not None:
                            response_txt += resp_chunk
                            if self.streaming_handler:
                                self.streaming_handler(resp_chunk)
                            else:
                                print(resp_chunk, end="", flush=True)                    
                    print() # newline after stream finished 
                    if self.streaming_handler:
                        self.streaming_handler("\n")                   
                else:
                    response_txt = response.choices[0].message.content  
                    
                if history_manager is not None:
                    history_manager.add_entry(llm_messages[-1]) # only add user message
                    history_manager.add_assistant_message(response_txt)
                return response_txt          
            except RateLimitError as e:
                print(f"Rate limit exceeded: {e}")
                # Implement retry logic or backoff strategy here
            except BadRequestError as e:
                print(f"Bad request error: {e.message}")  
            except OpenAIError as e:
                print(f"An OpenAI API error occurred: {e}")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                
        return None
    
    
    def invoke_model_stream(self, prompt=None, 
                     messages = None, 
                     model_id:str = None,
                     max_tokens:int = 0, 
                     max_completion_tokens:int = 0, 
                     temperature=0.1,
                     system_prompt:str = None,
                     history_manager:LLMHistoryManager = None,
                     )->str:        
        return self.invoke_model(prompt=prompt, 
                                 messages=messages, 
                                 model_id=model_id,
                                 max_tokens=max_tokens, 
                                 max_completion_tokens=max_completion_tokens, 
                                 temperature=temperature,
                                 system_prompt=system_prompt,
                                 history_manager=history_manager,
                                 streaming=True)
    
