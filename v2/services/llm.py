"""LLM service — async completion, async streaming, JSON mode, provider fallback chain."""

import json
import logging
from pathlib import Path
from typing import Any, AsyncGenerator

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# Language name mapping
LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "de": "German",
    "it": "Italian",
    "ru": "Russian",
    "eo": "Esperanto",
    "sl": "Slovenian",
}

SYSTEM_DETAILED = "You are a helpful travel assistant. Always respond with valid JSON."
SYSTEM_CONCISE = "You are a concise travel planner. Always respond with valid JSON."


def get_language_name(code: str) -> str:
    """Get full language name from code."""
    return LANGUAGE_NAMES.get(code, "English")


def load_prompt(name: str) -> str:
    """Load a prompt template from the prompts directory."""
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")


def build_prompt(
    active_prompt: str,
    duration: int,
    country: str,
    activities: str,
    language: str = "en",
) -> tuple[str, str, int]:
    """Build system prompt, user prompt, and max_tokens from template.

    Returns (system_prompt, user_prompt, max_tokens).
    """
    language_name = get_language_name(language)
    language_instruction = ""
    if language != "en":
        language_instruction = (
            f"\nIMPORTANT: Write all descriptions in {language_name}. "
            f"Keep 'city' values in English only."
        )

    template = load_prompt(active_prompt)
    user_prompt = template.format(
        duration=duration,
        country=country,
        activities=activities,
        language_instruction=language_instruction,
    )

    if active_prompt == "concise":
        system_prompt = SYSTEM_CONCISE
        max_tokens = min(300 * duration, 2500)
    else:
        system_prompt = SYSTEM_DETAILED
        max_tokens = min(500 * duration, 4000)

    return system_prompt, user_prompt, max_tokens


def create_client(provider_config: dict[str, str | None]) -> Any:
    """Create an async LLM client for the given provider config."""
    if provider_config["provider"] == "Anthropic":
        import anthropic
        return anthropic.AsyncAnthropic(api_key=provider_config["api_key"])
    else:
        from openai import AsyncOpenAI
        kwargs: dict[str, Any] = {"api_key": provider_config["api_key"]}
        if provider_config.get("base_url"):
            kwargs["base_url"] = provider_config["base_url"]
        return AsyncOpenAI(**kwargs)


async def _call_provider(
    client: Any,
    config: dict[str, str | None],
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float,
) -> str:
    """Call a single LLM provider asynchronously, requesting JSON output."""
    if config["provider"] == "Anthropic":
        response = await client.messages.create(
            model=config["model"],
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text
    else:
        response = await client.chat.completions.create(
            model=config["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content


async def llm_complete(
    clients: list[tuple[Any, dict[str, str | None]]],
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 2000,
    temperature: float = 0.7,
) -> dict:
    """Call LLM asynchronously and return parsed JSON. Tries providers in priority order."""
    last_error: Exception | None = None

    for client, config in clients:
        try:
            logger.info(f"Trying {config['provider']} ({config['model']})...")
            raw = await _call_provider(client, config, system_prompt, user_prompt, max_tokens, temperature)
            logger.info(f"Success with {config['provider']}")
            return parse_json_response(raw)
        except Exception as e:
            last_error = e
            logger.warning(f"{config['provider']} failed: {e} — trying next provider")

    raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")


def parse_json_response(raw: str) -> dict:
    """Parse LLM response as JSON, handling markdown code fences."""
    text = raw.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)


async def _stream_provider(
    client: Any,
    config: dict[str, str | None],
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float,
) -> AsyncGenerator[str, None]:
    """Stream text chunks from a single LLM provider asynchronously."""
    if config["provider"] == "Anthropic":
        async with client.messages.stream(
            model=config["model"],
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            async for text in stream.text_stream:
                yield text
    else:
        response = await client.chat.completions.create(
            model=config["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


async def llm_stream(
    clients: list[tuple[Any, dict[str, str | None]]],
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 2000,
    temperature: float = 0.7,
) -> AsyncGenerator[str, None]:
    """Stream LLM response asynchronously. Tries providers in priority order."""
    last_error: Exception | None = None

    for client, config in clients:
        try:
            logger.info(f"Streaming from {config['provider']} ({config['model']})...")
            yielded = False
            async for chunk in _stream_provider(client, config, system_prompt, user_prompt, max_tokens, temperature):
                yielded = True
                yield chunk
            if yielded:
                logger.info(f"Stream complete from {config['provider']}")
                return
        except Exception as e:
            last_error = e
            logger.warning(f"{config['provider']} stream failed: {e} — trying next provider")

    raise RuntimeError(f"All LLM providers failed to stream. Last error: {last_error}")
