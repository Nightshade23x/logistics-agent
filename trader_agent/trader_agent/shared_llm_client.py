"""Provider-agnostic LLM client for the agent reasoning layer."""

import os
from abc import ABC, abstractmethod
from dotenv import load_dotenv

load_dotenv()


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        ...


class GeminiProvider(LLMProvider):
    def __init__(self, model: str = "gemini-2.5-flash") -> None:
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        self._model = genai.GenerativeModel(model)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self._model.generate_content(f"{system_prompt}\n\n{user_prompt}")
        return response.text


def build_llm_provider() -> LLMProvider:
    return GeminiProvider()