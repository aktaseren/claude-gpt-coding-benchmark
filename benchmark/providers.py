from __future__ import annotations

import os
from typing import Any, Protocol

from .models import ModelResponse
from .prompts import SYSTEM_INSTRUCTIONS


class ProviderError(RuntimeError):
    """Raised when a model provider cannot produce a response."""


class ModelProvider(Protocol):
    provider: str
    model: str

    def generate(self, prompt: str) -> ModelResponse:
        ...


def parse_model_ref(value: str) -> tuple[str, str]:
    provider, separator, model = value.partition(":")
    if not separator or not provider or not model:
        raise ValueError(
            "Model reference must use PROVIDER:MODEL, for example "
            "openai:gpt-model-id"
        )
    provider = provider.lower()
    if provider not in {"openai", "anthropic"}:
        raise ValueError("Only the openai and anthropic providers are supported")
    return provider, model


def _usage_value(usage: Any, name: str) -> int | None:
    if usage is None:
        return None
    value = getattr(usage, name, None)
    if value is None and isinstance(usage, dict):
        value = usage.get(name)
    return int(value) if value is not None else None


class OpenAIProvider:
    provider = "openai"

    def __init__(self, model: str, api_key: str | None = None) -> None:
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

    def generate(self, prompt: str) -> ModelResponse:
        if not self.api_key:
            raise ProviderError("OPENAI_API_KEY is not set")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProviderError(
                "Install the OpenAI SDK with: python -m pip install openai"
            ) from exc

        try:
            client = OpenAI(api_key=self.api_key)
            response = client.responses.create(
                model=self.model,
                instructions=SYSTEM_INSTRUCTIONS,
                input=prompt,
                store=False,
            )
        except Exception as exc:
            raise ProviderError(f"OpenAI request failed: {exc}") from exc

        text = str(getattr(response, "output_text", "") or "")
        usage = getattr(response, "usage", None)
        return ModelResponse(
            text=text,
            input_tokens=_usage_value(usage, "input_tokens"),
            output_tokens=_usage_value(usage, "output_tokens"),
        )


class AnthropicProvider:
    provider = "anthropic"

    def __init__(self, model: str, api_key: str | None = None) -> None:
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

    def generate(self, prompt: str) -> ModelResponse:
        if not self.api_key:
            raise ProviderError("ANTHROPIC_API_KEY is not set")
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise ProviderError(
                "Install the Anthropic SDK with: python -m pip install anthropic"
            ) from exc

        try:
            client = Anthropic(api_key=self.api_key)
            response = client.messages.create(
                model=self.model,
                max_tokens=16_000,
                system=SYSTEM_INSTRUCTIONS,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:
            raise ProviderError(f"Anthropic request failed: {exc}") from exc

        blocks = getattr(response, "content", []) or []
        text = "".join(
            str(getattr(block, "text", ""))
            for block in blocks
            if getattr(block, "type", "text") == "text"
        )
        usage = getattr(response, "usage", None)
        return ModelResponse(
            text=text,
            input_tokens=_usage_value(usage, "input_tokens"),
            output_tokens=_usage_value(usage, "output_tokens"),
        )


def make_provider(provider: str, model: str) -> ModelProvider:
    provider = provider.lower()
    if provider == "openai":
        return OpenAIProvider(model)
    if provider == "anthropic":
        return AnthropicProvider(model)
    raise ValueError(f"Unsupported provider: {provider}")
