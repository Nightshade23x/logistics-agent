"""Provider-agnostic LLM client for the agent reasoning layer."""

import os
from abc import ABC, abstractmethod
from dotenv import load_dotenv

load_dotenv()


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Send a prompt and return the model's text response."""
        ...


class OpenAIProvider(LLMProvider):
    def __init__(self, model: str = "gpt-4o-mini") -> None:
        from openai import OpenAI
        self._client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self._model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=500,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content


def build_llm_provider() -> LLMProvider:
    """Factory — swap this to change provider for the whole agent at once."""
    return OpenAIProvider()