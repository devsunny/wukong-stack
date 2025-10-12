import getpass
import json
import logging
from pathlib import Path
from typing import Any, Callable, List, Optional
from openai import OpenAI, OpenAIError, RateLimitError, BadRequestError
import httpx

from .history_manager import LLMHistoryManager
from .function_tools import autodiscover_tools

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

    
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
                 max_retries:int = 3,   
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
        self.max_retries = max_retries  
        
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
                     history_manager:LLMHistoryManager = None, 
                     include_history: Optional[int] = None)-> List[dict[str, Any]]:        
        limit = include_history if include_history is not None else self.history_limit
        hist_man = history_manager if history_manager is not None else self.history_manager 
        hist_msgs = hist_man.get_chat_history(limit) if hist_man is not None else []        
        return hist_msgs + messages
    
    def invoke_model(self, prompt=None, 
                     messages = None, 
                     model_id:str = None,
                     max_tokens:Optional[int] = None, 
                     max_completion_tokens:Optional[int] = None, 
                     temperature:float = None,
                     system_prompt: Optional[str] = None,
                     history_manager:LLMHistoryManager = None,
                     tools:List[Callable]=None,
                     streaming:bool = False,
                     reasoning_effort: Optional[str]  = None,        
                     context: Optional[dict[str, Any]] = None,        
                     include_history: Optional[int] = None,
        )->str:
                            
        llm = self._get_llm()        
        req_max_tokens = None
        if max_tokens is not None and max_completion_tokens is not None:
            req_max_tokens = max(max_tokens, max_completion_tokens)
        elif max_tokens is not None:
            req_max_tokens = max_tokens
        elif max_completion_tokens is not None:
            req_max_tokens = max_completion_tokens        
        
        hist_man = history_manager if history_manager is not None else self.history_manager
        
        input_messages = messages if messages is not None else [{"role": "user", "content": prompt}]
        if hist_man and include_history is not None and include_history > 0:
            llm_messages = self.get_messages_with_history(input_messages, 
                                                          history_manager=hist_man, 
                                                          include_history=include_history) 
        else:
            llm_messages = input_messages
        
        if system_prompt:
            llm_messages.insert(0, {"role": "system", "content": system_prompt})
        
        if hist_man is not None:
            hist_man.add_entry(llm_messages[-1]) # only add user message
            
        selected_model = model_id if model_id is not None else self.model_id
        llm_tools, funct_map = autodiscover_tools(tools) if tools is not None else (None, {})
                
        chat_params = {
            "model": selected_model,  # or any other model you want to use
            "max_completion_tokens": req_max_tokens,
            "messages": llm_messages,
            "temperature": temperature,
            "stream": streaming,
            "tools": llm_tools,
        }
        
        for retry in range(self.max_retries):
            try:                
                response = llm.chat.completions.create(        
                   **chat_params             
                )  
                response_txt = ""              
                if streaming:                    
                    return self._handle_stream(response, funct_map,
                                                messages=llm_messages, 
                                                model_id=model_id,
                                                max_tokens=max_tokens, 
                                                max_completion_tokens=max_completion_tokens, 
                                                temperature=temperature,
                                                reasoning_effort=reasoning_effort,
                                                context=context,
                                                history_manager=hist_man)       
                else:
                    return self._handle_non_streaming_response(response, funct_map,
                                                messages=llm_messages, 
                                                model_id=model_id,
                                                max_tokens=max_tokens, 
                                                max_completion_tokens=max_completion_tokens, 
                                                temperature=temperature,
                                                reasoning_effort=reasoning_effort,
                                                context=context,
                                                history_manager=hist_man)                   
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
    
    def _execute_tool(
        self,
        tool: Callable,
        assistant_content: str,
        tool_call_id: str,
        tool_name: str,
        tool_args: dict,
        context: Optional[dict] = None,
    ) -> str:
        tool_messages = [
            {
                "role": "assistant",
                "content": assistant_content or None,
                "tool_calls": [
                    {
                        "id": tool_call_id,
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": json.dumps(tool_args),
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": tool_name,
                "content": None,
            },
        ]
        try:
            if context:
                tool_args["context"] = context

            result = tool(**tool_args)
        except Exception as e:
            result = f"Error executing tool {tool_name}: {str(e)}"

        tool_messages[-1]["content"] = json.dumps(result)
        return tool_messages
    
    def _handle_non_streaming_response(self, response, tools_mapping, messages = None,
                        model_id:str = None,
                     max_tokens:Optional[int] = None, 
                     max_completion_tokens:Optional[int] = None, 
                     temperature:float = None,                     
                     history_manager:LLMHistoryManager = None,
                     tools:List[Callable]=None,
                     streaming:bool = False,
                     reasoning_effort: Optional[str]  = None,        
                     context: Optional[dict[str, Any]] = None):
        
        assistant_content = ""
        tool_call_id = None
        tool_name = None
        tool_args_json = ""
        logger.info("Response finish_reason:", response.choices[0].finish_reason)
        
        if response.choices[0].finish_reason == "stop":
            assistant_content = response.choices[0].message.content            

        tcs = getattr(response.choices[0].message, "tool_calls", None)
        if tcs:
            call = tcs[0]
            tool_call_id = call.id or tool_call_id
            if call.function:
                if call.function.name:
                    tool_name = call.function.name
                if call.function.arguments:
                    tool_args_json += call.function.arguments
        if tool_call_id and tool_name:
            args = json.loads(tool_args_json or "{}")
            fuct, stateless = tools_mapping.get(tool_name)
            ctx = context if not stateless else None
            tool_messages = self._execute_tool(
                fuct, assistant_content, tool_call_id, tool_name, args, ctx
            )
            if history_manager is not None:
                history_manager.add_entry(tool_messages[0])
            messages.extend(tool_messages)
            return self.invoke_model(
                model_id=model_id,
                max_tokens=max_tokens,
                max_completion_tokens=max_completion_tokens,               
                messages=messages,
                tools=tools,
                temperature=temperature,
                reasoning_effort=reasoning_effort,
                context=ctx,
                history_manager=history_manager,
                streaming=streaming,
                include_history=0,  # avoid duplicating history
            )
        if history_manager is not None:
            history_manager.add_assistant_message(assistant_content)    
        return assistant_content    
    
    def _handle_stream(self, response, tools_mapping, messages = None, 
                     model_id:str = None,
                     max_tokens:Optional[int] = None, 
                     max_completion_tokens:Optional[int] = None, 
                     temperature:float = None,                     
                     history_manager:LLMHistoryManager = None,
                     tools:List[Callable]=None,
                     streaming:bool = False,
                     reasoning_effort: Optional[str]  = None,        
                     context: Optional[dict[str, Any]] = None,        
                     ):
        assistant_content = ""
        tool_call_id = None
        tool_name = None
        tool_args_json = ""
        is_tool_call = False
        for chunk in response:
            # print(chunk)
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue
            # Text tokens
            if getattr(delta, "content", None):
                if self.stream_handler:
                    self.stream_handler(delta.content)
                assistant_content += delta.content

            # Tool call deltas
            tcs = getattr(delta, "tool_calls", None)
            if tcs:
                if is_tool_call is False:
                    if self.stream_handler:
                        self.stream_handler("\n")
                    is_tool_call = True
                call = tcs[0]
                tool_call_id = call.id or tool_call_id
                if call.function:
                    if call.function.name:
                        tool_name = call.function.name
                    if call.function.arguments:
                        if self.stream_handler:
                            self.stream_handler(call.function.arguments)
                        tool_args_json += call.function.arguments
                if self.stream_handler:
                    self.stream_handler("\n")

        if tool_call_id and tool_name:
            args = json.loads(tool_args_json or "{}")
            fuct, stateless = tools_mapping.get(tool_name)
            ctx = context if not stateless else None
            tool_messages = self._execute_tool(
                fuct, assistant_content, tool_call_id, tool_name, args, ctx
            )
            messages.extend(tool_messages)
            if history_manager is not None:
                history_manager.add_entry(tool_messages[0])
            return self.invoke_model(
                model_id=model_id,
                max_tokens=max_tokens,
                max_completion_tokens=max_completion_tokens,               
                messages=messages,
                tools=tools,
                temperature=temperature,
                reasoning_effort=reasoning_effort,
                context=ctx,
                history_manager=history_manager,
                streaming=streaming,
                include_history=0,  # avoid duplicating history
            )
            
        if history_manager is not None:
            history_manager.add_assistant_message(assistant_content)    
        return assistant_content
            
    
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
    
    


