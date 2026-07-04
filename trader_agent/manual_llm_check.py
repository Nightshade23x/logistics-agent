"""One-off check that the OpenAI key and client work. Not part of the test suite."""

from trader_agent.shared_llm_client import build_llm_provider

llm = build_llm_provider()
result = llm.generate(
    system_prompt="You are a helpful assistant.",
    user_prompt="Say 'API connection successful' and nothing else.",
)
print(result)