from ..wukong_config import wukong_config, WukongConfigManager
from .history_manager import LLMHistoryManager
from .llm_client import LLMClient



def create_llm_client(model_id: str = None,
                      base_url: str = None,
                      api_key: str = None,
                      max_completion_tokens: int = None,
                      fallback_models: list = None,
                      history_limit: int = 100,
                      streaming_handler = None,
                      history_manager: LLMHistoryManager = None
                      ) -> LLMClient: 
        base_url = wukong_config.get("llm.base_url", None)
        api_key = wukong_config.get("llm.api_key", None)
        model_id = wukong_config.get("llm.model_id", None)    
        assert model_id is not None, "model_id must be specified in [text_to_sql] section of .wukong.toml"
        model_id = model_id[0] if isinstance(model_id, list) and len(model_id) > 0  else "gpt-5"        
        max_completion_tokens = wukong_config.get("llm.max_completion_tokens", 32000) 
        fallback_models = wukong_config.get("llm.fallback_models", [])
        history_limit = wukong_config.get("llm.history_limit", 100)               
        llm_client = LLMClient(
            model_id=model_id,
            base_url=base_url,
            api_key=api_key,
            max_completion_tokens=max_completion_tokens,
            fallback_models=fallback_models,
            history_manager=history_manager,
            history_limit=history_limit,
            streaming_handler=streaming_handler
        )
        return llm_client