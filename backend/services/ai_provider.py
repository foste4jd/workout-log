"""
Shared AI provider abstraction.

Swap _get_provider() to change the LLM globally.
Both ai_trainer_service and interpret_service import from here.
"""

import os
import logging

from backend import ai_config

logger = logging.getLogger(__name__)


class AIProvider:
    def complete(self, messages: list, temperature: float = 0.3) -> str:
        raise NotImplementedError

    def complete_mini(self, messages: list) -> str:
        return self.complete(messages, temperature=0.1)


class OpenAIProvider(AIProvider):
    _MAIN_MODEL = ai_config.AI_MODEL
    _MINI_MODEL = ai_config.AI_MINI_MODEL

    def __init__(self):
        from openai import OpenAI
        self._client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.last_usage: dict = {}

    def complete(self, messages: list, temperature: float = 0.3) -> str:
        resp = self._client.chat.completions.create(
            model=self._MAIN_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=temperature,
            max_tokens=ai_config.MAX_OUTPUT_TOKENS,
        )
        if resp.usage:
            self.last_usage = {
                "input_tokens":  resp.usage.prompt_tokens,
                "output_tokens": resp.usage.completion_tokens,
            }
        return resp.choices[0].message.content

    def complete_mini(self, messages: list) -> str:
        resp = self._client.chat.completions.create(
            model=self._MINI_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=ai_config.MAX_OUTPUT_TOKENS,
        )
        if resp.usage:
            self.last_usage = {
                "input_tokens":  resp.usage.prompt_tokens,
                "output_tokens": resp.usage.completion_tokens,
            }
        return resp.choices[0].message.content


class AnthropicProvider(AIProvider):
    _MAIN_MODEL = os.environ.get("AI_MODEL", "claude-sonnet-4-6")
    _MINI_MODEL = os.environ.get("AI_MINI_MODEL", "claude-haiku-4-5-20251001")

    def __init__(self):
        import anthropic
        self._client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.last_usage: dict = {}

    def _call(self, model: str, messages: list, temperature: float) -> str:
        system   = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_msgs = [m for m in messages if m["role"] != "system"]
        resp = self._client.messages.create(
            model=model,
            max_tokens=ai_config.MAX_OUTPUT_TOKENS,
            system=system,
            messages=user_msgs,
            temperature=temperature,
        )
        self.last_usage = {
            "input_tokens":  resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
        }
        return resp.content[0].text

    def complete(self, messages: list, temperature: float = 0.3) -> str:
        return self._call(self._MAIN_MODEL, messages, temperature)

    def complete_mini(self, messages: list) -> str:
        return self._call(self._MINI_MODEL, messages, temperature=0.1)


def get_provider() -> AIProvider:
    """Swap this to change the LLM provider globally."""
    return OpenAIProvider()


def truncate(s, n: int) -> str:
    """Hard-truncate string to n chars."""
    if not s:
        return s or ""
    s = str(s)
    return s if len(s) <= n else s[:n - 1] + "…"
