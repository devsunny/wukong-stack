import openai
from wukong.wukong_config import WukongConfigManager


class LLMClient:
    def __init__(self):
        self.cfg_man = WukongConfigManager()
        # Configure the OpenAI client to use Ollama's API
        self.openai_client = openai.OpenAI(
            base_url=self.cfg_man.get("llm.base_url"),
            api_key=self.cfg_man.get("llm.api_key"),
            timeout=1000,
        )

    def invoke_llm_stream(self, prompt: str, model: str = None, max_tokens: int = 8000):
        response = self.openai_client.chat.completions.create(
            model=model or self.cfg_man.get("llm.model_id")[0],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in response:
            if chunk and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
        return

    def invoke_llm(self, prompt: str, model: str = None, max_tokens: int = 8000) -> str:
        response = self.openai_client.chat.completions.create(
            model=model or self.cfg_man.get("llm.model_id")[0],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            stream=False,
        )
        return response.choices[0].message.content
