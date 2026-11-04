"""LLM provider selection.

If ANTHROPIC_API_KEY is set (in the environment or in .env), the agents use
Claude. Otherwise they fall back to a mock that returns placeholder text, so the
app still starts without any key.

Agents only need one method: `await llm.agenerate([prompt])`, returning an object
with `.generations[0][0].text`.
"""

import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "claude-sonnet-5-5"


class _Result:
    def __init__(self, text: str):
        class _Gen:
            def __init__(self, t):
                self.text = t

        self.generations = [[_Gen(text)]]


class MockLLM:
    name = "mock"
    model = None

    async def agenerate(self, prompts):
        return _Result("Mock LLM response")


class ClaudeLLM:
    name = "claude"

    def __init__(self, api_key: str, model: str):
        from anthropic import AsyncAnthropic

        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    async def agenerate(self, prompts):
        message = await self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=(
                "You are an AI agent inside a CRM system. Follow the output format "
                "requested in the prompt exactly. Do not add preambles or commentary."
            ),
            messages=[{"role": "user", "content": prompts[0]}],
        )
        text = "".join(b.text for b in message.content if getattr(b, "type", "") == "text")
        return _Result(text)


def get_llm():
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    # The placeholder values shipped in .env.example are not real keys.
    if key and not key.startswith("sk-ant-your") and "your" not in key.lower():
        return ClaudeLLM(key, os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL))
    return MockLLM()
