"""LLM Engine — pluggable, cost-optimized, with automatic fallback.

Priority:
  1. Groq FREE API (Llama 3.1 8B / 3.3 70B) — $0/month, ultra-fast
  2. Ollama local (any model, fully free)
  3. Together AI ($0.18/1M tokens) — cheap fallback
  4. OpenAI GPT-4o-mini ($0.15/1M tokens) — quality fallback
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator

import structlog

from config import settings

log = structlog.get_logger()


class LLMEngine:
    """Unified LLM interface with automatic provider fallback and rate-limit awareness."""

    def __init__(self) -> None:
        self._provider = settings.LLM_PROVIDER
        self._model = settings.LLM_MODEL
        self._groq_client: Any | None = None
        self._openai_client: Any | None = None
        self._groq_request_count: int = 0
        self._groq_reset_time: datetime = datetime.utcnow() + timedelta(minutes=1)
        self._GROQ_RPM_LIMIT = 30  # Free tier: 30 req/min per model

    async def _init_groq(self) -> Any:
        """Lazy-init Groq client."""
        if self._groq_client is None:
            try:
                from groq import AsyncGroq

                if settings.GROQ_API_KEY:
                    self._groq_client = AsyncGroq(
                        api_key=settings.GROQ_API_KEY.get_secret_value()
                    )
            except ImportError:
                log.warning("groq package not installed")
        return self._groq_client

    async def _init_openai(self) -> Any:
        """Lazy-init OpenAI client."""
        if self._openai_client is None:
            try:
                from openai import AsyncOpenAI

                if settings.OPENAI_API_KEY:
                    self._openai_client = AsyncOpenAI(
                        api_key=settings.OPENAI_API_KEY.get_secret_value()
                    )
            except ImportError:
                log.warning("openai package not installed")
        return self._openai_client

    def _check_groq_rate_limit(self) -> bool:
        """Returns True if we are under Groq rate limit."""
        now = datetime.utcnow()
        if now >= self._groq_reset_time:
            self._groq_request_count = 0
            self._groq_reset_time = now + timedelta(minutes=1)
        return self._groq_request_count < self._GROQ_RPM_LIMIT

    async def chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> str:
        """Generate a chat completion with automatic provider fallback."""
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        providers = self._get_provider_order()
        last_error: Exception | None = None

        for provider in providers:
            try:
                response = await self._call_provider(
                    provider, messages, tools, temperature, max_tokens
                )
                return response
            except Exception as exc:
                log.warning(
                    "LLM provider failed, trying next",
                    provider=provider,
                    error=str(exc),
                )
                last_error = exc
                continue

        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")

    def _get_provider_order(self) -> list[str]:
        """Return provider priority list, skipping unavailable ones."""
        primary = self._provider
        order = [primary]

        # Add fallbacks
        fallbacks = ["groq", "ollama", "together", "openai"]
        for fb in fallbacks:
            if fb != primary:
                order.append(fb)
        return order

    async def _call_provider(
        self,
        provider: str,
        messages: list[dict],
        tools: list[dict] | None,
        temperature: float,
        max_tokens: int,
    ) -> str:
        if provider == "groq":
            return await self._call_groq(messages, tools, temperature, max_tokens)
        elif provider == "ollama":
            return await self._call_ollama(messages, temperature, max_tokens)
        elif provider == "together":
            return await self._call_together(messages, temperature, max_tokens)
        elif provider == "openai":
            return await self._call_openai(messages, tools, temperature, max_tokens)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    async def _call_groq(
        self,
        messages: list[dict],
        tools: list[dict] | None,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Call Groq API (FREE tier — Llama 3)."""
        if not settings.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY not set")

        if not self._check_groq_rate_limit():
            log.warning("Groq rate limit approaching, falling back")
            raise RuntimeError("Groq rate limit")

        client = await self._init_groq()
        if client is None:
            raise RuntimeError("Groq client unavailable")

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        self._groq_request_count += 1
        response = await client.chat.completions.create(**kwargs)

        # Handle tool calls
        choice = response.choices[0]
        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            # Return serialized tool call for the caller to handle
            return json.dumps(
                {
                    "tool_calls": [
                        {
                            "name": tc.function.name,
                            "arguments": json.loads(tc.function.arguments),
                        }
                        for tc in choice.message.tool_calls
                    ]
                }
            )

        return choice.message.content or ""

    async def _call_ollama(
        self, messages: list[dict], temperature: float, max_tokens: int
    ) -> str:
        """Call local Ollama (completely free)."""
        import aiohttp

        payload = {
            "model": settings.OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{settings.OLLAMA_BASE_URL}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Ollama error: {resp.status}")
                data = await resp.json()
                return data["message"]["content"]

    async def _call_together(
        self, messages: list[dict], temperature: float, max_tokens: int
    ) -> str:
        """Call Together AI (very cheap fallback — $0.18/1M tokens)."""
        if not settings.TOGETHER_API_KEY:
            raise RuntimeError("TOGETHER_API_KEY not set")

        import aiohttp

        headers = {
            "Authorization": f"Bearer {settings.TOGETHER_API_KEY.get_secret_value()}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "mistralai/Mistral-7B-Instruct-v0.2",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.together.xyz/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Together AI error: {resp.status}")
                data = await resp.json()
                return data["choices"][0]["message"]["content"]

    async def _call_openai(
        self,
        messages: list[dict],
        tools: list[dict] | None,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Call OpenAI GPT-4o-mini (quality fallback — $0.15/1M tokens)."""
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY not set")

        client = await self._init_openai()
        if client is None:
            raise RuntimeError("OpenAI client unavailable")

        kwargs: dict[str, Any] = {
            "model": "gpt-4o-mini",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = await client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Stream chat completions token-by-token (Groq only for now)."""
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        client = await self._init_groq()
        if client is None or not settings.GROQ_API_KEY:
            # Fall back to non-streaming
            result = await self.chat(messages, temperature=temperature)
            yield result
            return

        stream = await client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content


# Singleton
_llm_engine: LLMEngine | None = None


def get_llm_engine() -> LLMEngine:
    global _llm_engine
    if _llm_engine is None:
        _llm_engine = LLMEngine()
    return _llm_engine
