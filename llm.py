"""LLM provider selection.

Provider choice, in order:
  1. LLM_PROVIDER=claude|deepseek|mock, if set
  2. ANTHROPIC_API_KEY set  -> Claude
  3. DEEPSEEK_API_KEY set   -> DeepSeek
  4. otherwise              -> a mock that returns placeholder text, so the app
                               still starts without any key
(Keys can be in the environment or in .env.)

Agents only need one method: `await llm.agenerate([prompt])`, returning an object
with `.generations[0][0].text`.
"""

import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "claude-sonnet-5-5"
DEFAULT_DEEPSEEK_MODEL = "deepseek-flash"
DEFAULT_DEEPSEEK_URL = "https://api.deepseek.com"

SYSTEM_PROMPT = (
    "You are an AI agent inside a CRM system. Follow the output format "
    "requested in the prompt exactly. Do not add preambles or commentary."
)


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
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompts[0]}],
        )
        text = "".join(b.text for b in message.content if getattr(b, "type", "") == "text")
        return _Result(text)


class DeepSeekLLM:
    """DeepSeek via its OpenAI-compatible /chat/completions endpoint (uses httpx)."""

    name = "deepseek"

    def __init__(self, api_key: str, model: str, base_url: str):
        self.api_key = api_key
        self.model = model
        self.url = base_url.rstrip("/") + "/chat/completions"

    async def agenerate(self, prompts):
        import httpx

        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "stream": False,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompts[0]},
            ],
        }
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                self.url,
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        if resp.status_code != 200:
            # Show the provider's own message, never the key
            raise RuntimeError(f"DeepSeek API error {resp.status_code}: {resp.text[:300]}")
        message = resp.json()["choices"][0]["message"]
        return _Result(message.get("content") or "")


def _real_key(name: str) -> str:
    """Return the key from the environment, or "" if unset or still a placeholder."""
    key = os.getenv(name, "").strip()
    return "" if (not key or "your" in key.lower()) else key


def get_llm():
    choice = os.getenv("LLM_PROVIDER", "").strip().lower()
    anthropic_key = _real_key("ANTHROPIC_API_KEY")
    deepseek_key = _real_key("DEEPSEEK_API_KEY")

    if choice == "mock":
        return MockLLM()
    if choice == "claude" and anthropic_key or (not choice and anthropic_key):
        return ClaudeLLM(anthropic_key, os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL))
    if choice == "deepseek" and deepseek_key or (not choice and deepseek_key):
        return DeepSeekLLM(
            deepseek_key,
            os.getenv("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL),
            os.getenv("DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_URL),
        )
    return MockLLM()
