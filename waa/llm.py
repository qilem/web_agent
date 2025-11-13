from typing import List, Dict, Any
import os

class LanguageModel:
    def __init__(self):
        pass

    def generate(self, messages: List[Dict[str, Any]]) -> str:
        raise NotImplementedError("Subclasses must implement this method")


class GeminiLanguageModel(LanguageModel):
    def __init__(self, model_name: str = "gemini-2.5-flash", api_key: str = None):
        super().__init__()
        self.model_name = model_name
        self.temperature = 0.0
        self.max_tokens = 8000
        self.top_p = 1.0

        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config={
                    "temperature": self.temperature,
                    "max_output_tokens": self.max_tokens,
                    "top_p": self.top_p,
                }
            )
        except ImportError:
            raise ImportError("google-generativeai package not installed. Install with: pip install google-generativeai")

    def generate(self, messages: List[Dict[str, Any]]) -> str:
        gemini_messages = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")

            if role == "system":
                gemini_messages.append({"role": "user", "parts": [content]})
            elif role == "user":
                gemini_messages.append({"role": "user", "parts": [content]})
            elif role == "assistant":
                gemini_messages.append({"role": "model", "parts": [content]})
            elif role == "tool":
                tool_content = content if isinstance(content, str) else str(content)
                gemini_messages.append({"role": "user", "parts": [f"Tool result: {tool_content}"]})

        try:
            chat = self.client.start_chat(history=gemini_messages[:-1] if len(gemini_messages) > 1 else [])
            response = chat.send_message(gemini_messages[-1]["parts"][0] if gemini_messages else "")
            return response.text
        except Exception as e:
            raise RuntimeError(f"Gemini API error: {str(e)}")


class MockLanguageModel(LanguageModel):
    def __init__(self, responses: List[str] = None):
        super().__init__()
        self.responses = responses or [
            '<tool_call>{"tool": "fs.read", "arguments": {"path": "package.json"}}</tool_call>',
            'Let me check the project structure.',
            '<tool_call>{"tool": "tests.run", "arguments": {"type": "all"}}</tool_call>',
            '<terminate>'
        ]
        self.call_count = 0

    def generate(self, messages: List[Dict[str, Any]]) -> str:
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return response

    def reset(self):
        self.call_count = 0


def create_language_model(model_name: str, **kwargs: Any) -> LanguageModel:
    """
    Factory function to create a language model instance based on the model name.

    Args:
        model_name (str): The name of the model to create.
                          e.g., "gemini-1.5-flash", "mock".
        **kwargs: Additional keyword arguments to pass to the model's constructor.

    Returns:
        LanguageModel: An instance of the specified language model.

    Raises:
        ValueError: If the model_name is unknown.
    """
    if model_name.startswith("gemini"):
        # 如果模型名字以 "gemini" 开头，就创建 GeminiLanguageModel
        return GeminiLanguageModel(model_name=model_name, **kwargs)
    elif model_name == "mock":
        # 如果模型名字是 "mock"，就创建 MockLanguageModel
        return MockLanguageModel(**kwargs)
    else:
        # 如果是不认识的名字，就报错
        raise ValueError(f"Unknown language model: {model_name}")