import json
from pathlib import Path
import openai
from wukong.wukong_config import WukongConfigManager


class LLMClient:

    def __init__(self):
        self.cfg_man = WukongConfigManager()
        # Configure the OpenAI client to use Ollama's API
        construc_args = {}
        if self.cfg_man.get("llm.base_url"):
            construc_args["base_url"] = self.cfg_man.get("llm.base_url")
        construc_args["api_key"] = self.cfg_man.get("llm.api_key", "ollama")
        construc_args["timeout"] = int(self.cfg_man.get("llm.timeout", "1000"))
        self.openai_client = openai.OpenAI(**construc_args)
        self.history = None
        self._load_history()

    def show_history(self):
        if not self.history:
            print("No conversation history.")
            return
        for entry in self.history:
            role = entry.get("role", "unknown")
            content = entry.get("content", "")
            print(f"{role.capitalize()}: {content}\n")

    def _load_history(self):
        if self.history is None:
            history_path = Path.home() / ".wukong" / "history.json"
            if history_path.exists():
                with open(history_path, "r") as f:
                    self.history = json.load(f)
            else:
                history_path.parent.mkdir(parents=True, exist_ok=True)
                self.history = []
        return self.history

    def clear_history(self):
        self.history = []
        history_path = Path.home() / ".wukong" / "history.json"
        if history_path.exists():
            history_path.unlink()

    def save_history(self):
        history_path = Path.home() / ".wukong" / "history.json"
        history_path.parent.mkdir(parents=True, exist_ok=True)
        with open(history_path, "w") as f:
            json.dump(self.history, f)

    def invoke_llm_stream(
        self,
        prompt: str,
        model: str = None,
        max_tokens: int = 8000,
        include_history: bool = True,
    ):
        messages = (
            self.history[-20:]
            if self.history and include_history is True
            else [{"role": "user", "content": prompt}]
        )
        response = self.openai_client.chat.completions.create(
            model=model or self.cfg_man.get("llm.model_id")[0],
            messages=messages,
            max_tokens=max_tokens,
            stream=True,
        )
        response_text = ""
        for chunk in response:
            # print(chunk)
            if chunk and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta.content:
                    delta_text = delta.content
                    response_text += delta_text
                    yield delta_text
        if include_history:
            self.history.append({"role": "user", "content": prompt})
            self.history.append({"role": "assistant", "content": response_text})
        # return response_text

    def invoke_llm(
        self,
        prompt: str,
        model: str = None,
        max_tokens: int = 8000,
        include_history: bool = True,
    ) -> str:
        messages = (
            self.history[-20:]
            if self.history and include_history is True
            else [{"role": "user", "content": prompt}]
        )
        response = self.openai_client.chat.completions.create(
            model=model or self.cfg_man.get("llm.model_id")[0],
            messages=messages,
            max_tokens=max_tokens,
            stream=False,
        )
        response_text = response.choices[0].message.content
        if include_history and response_text:
            self.history.append({"role": "user", "content": prompt})
            self.history.append({"role": "assistant", "content": response_text})
        return response_text
