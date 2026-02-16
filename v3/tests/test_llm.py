"""Tests for services/llm.py — async LLM completion, streaming, prompt building, &&& parsing."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from v3.services.llm import (
    build_prompt,
    get_language_name,
    llm_complete,
    llm_stream,
    load_prompt,
    parse_marker_text,
)


class TestGetLanguageName:

    def test_known_languages(self):
        assert get_language_name("en") == "English"
        assert get_language_name("de") == "German"
        assert get_language_name("sl") == "Slovenian"

    def test_unknown_defaults_to_english(self):
        assert get_language_name("xx") == "English"


class TestLoadPrompt:

    def test_load_detailed(self):
        text = load_prompt("detailed")
        assert "{duration}" in text
        assert "{country}" in text
        assert "&&&" in text

    def test_load_concise(self):
        text = load_prompt("concise")
        assert "{duration}" in text
        assert "&&&" in text

    def test_load_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            load_prompt("nonexistent_prompt_xyz")


class TestBuildPrompt:

    def test_detailed_prompt(self):
        system, user, max_tokens = build_prompt("detailed", 5, "Italy", "hiking")
        assert "travel assistant" in system.lower()
        assert "Italy" in user
        assert "hiking" in user
        assert max_tokens == 2500  # min(500*5, 4000)

    def test_concise_prompt(self):
        system, user, max_tokens = build_prompt("concise", 3, "France", "food")
        assert "concise" in system.lower()
        assert max_tokens == 900  # min(300*3, 2500)

    def test_language_instruction_added(self):
        _, user, _ = build_prompt("detailed", 3, "Japan", "temples", language="de")
        assert "German" in user
        assert "English" in user  # city names stay English

    def test_no_language_instruction_for_english(self):
        _, user, _ = build_prompt("detailed", 3, "Japan", "temples", language="en")
        assert "German" not in user

    def test_max_tokens_capped(self):
        _, _, max_tokens = build_prompt("detailed", 20, "Europe", "all")
        assert max_tokens == 4000  # capped


class TestParseMarkerText:

    def test_single_day(self):
        text = "&&& Rome\n### Day 1: Arrival\n- Visit Colosseum\n- Evening pasta"
        result = parse_marker_text(text)
        assert len(result) == 1
        assert result[0]["city"] == "Rome"
        assert "Colosseum" in result[0]["content"]

    def test_multiple_days(self):
        text = (
            "&&& Rome\n### Day 1: Rome\n- Colosseum\n\n"
            "&&& Florence\n### Day 2: Florence\n- Uffizi Gallery\n\n"
            "&&& Venice\n### Day 3: Venice\n- Grand Canal"
        )
        result = parse_marker_text(text)
        assert len(result) == 3
        assert result[0]["city"] == "Rome"
        assert result[1]["city"] == "Florence"
        assert result[2]["city"] == "Venice"

    def test_no_markers(self):
        result = parse_marker_text("Just some text without markers")
        assert result == []

    def test_empty_city_ignored(self):
        text = "&&&\n### Day 1\n- stuff\n&&& Paris\n### Day 2\n- Eiffel Tower"
        result = parse_marker_text(text)
        assert len(result) == 1
        assert result[0]["city"] == "Paris"

    def test_whitespace_in_city_trimmed(self):
        text = "&&&   Barcelona  \n### Day 1: Barcelona\n- La Rambla"
        result = parse_marker_text(text)
        assert result[0]["city"] == "Barcelona"

    def test_content_preserves_lines(self):
        text = "&&& Tokyo\n### Day 1: Tokyo\n- Morning: Tsukiji\n- Afternoon: Shibuya"
        result = parse_marker_text(text)
        assert "Morning: Tsukiji" in result[0]["content"]
        assert "Afternoon: Shibuya" in result[0]["content"]


@pytest.mark.asyncio
class TestLlmComplete:

    async def test_openai_provider_returns_text(self):
        """OpenAI-compatible provider should return raw text (no JSON mode)."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='&&& Rome\n### Day 1: Arrival\n- Visit Colosseum'))]
        )
        config = {"provider": "DeepSeek", "model": "deepseek-chat", "api_key": "k", "base_url": None}

        result = await llm_complete([(mock_client, config)], "system", "prompt")
        assert isinstance(result, str)
        assert "&&&" in result

        # Verify NO json_object format was requested
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert "response_format" not in call_kwargs

    async def test_anthropic_provider(self):
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text='&&& Paris\n### Day 1: Paris\n- Eiffel Tower')]
        )
        config = {"provider": "Anthropic", "model": "claude-sonnet-4-5", "api_key": "k", "base_url": None}

        result = await llm_complete([(mock_client, config)], "system", "prompt")
        assert isinstance(result, str)
        assert "Paris" in result

    async def test_fallback_on_failure(self):
        failing = AsyncMock()
        failing.chat.completions.create.side_effect = Exception("Rate limit")
        fail_config = {"provider": "DeepSeek", "model": "m", "api_key": "k", "base_url": None}

        working = AsyncMock()
        working.messages.create.return_value = MagicMock(
            content=[MagicMock(text='&&& Fallback\n### Day 1\n- stuff')]
        )
        work_config = {"provider": "Anthropic", "model": "m", "api_key": "k", "base_url": None}

        result = await llm_complete([(failing, fail_config), (working, work_config)], "sys", "prompt")
        assert "Fallback" in result

    async def test_all_fail_raises(self):
        failing = AsyncMock()
        failing.chat.completions.create.side_effect = Exception("Down")
        config = {"provider": "DeepSeek", "model": "m", "api_key": "k", "base_url": None}

        with pytest.raises(RuntimeError, match="All LLM providers failed"):
            await llm_complete([(failing, config)], "sys", "prompt")


@pytest.mark.asyncio
class TestLlmStream:

    async def test_openai_streaming(self):
        chunk1 = MagicMock(choices=[MagicMock(delta=MagicMock(content='&&& Rome'))])
        chunk2 = MagicMock(choices=[MagicMock(delta=MagicMock(content='\n### Day 1'))])
        chunk3 = MagicMock(choices=[MagicMock(delta=MagicMock(content=None))])

        mock_client = AsyncMock()

        async def mock_stream():
            for c in [chunk1, chunk2, chunk3]:
                yield c

        mock_client.chat.completions.create.return_value = mock_stream()
        config = {"provider": "DeepSeek", "model": "m", "api_key": "k", "base_url": None}

        chunks = []
        async for chunk in llm_stream([(mock_client, config)], "sys", "prompt"):
            chunks.append(chunk)
        assert chunks == ['&&& Rome', '\n### Day 1']

    async def test_anthropic_streaming(self):
        async def mock_text_stream():
            for t in ['&&& Paris', '\n### Day 1']:
                yield t

        mock_stream_obj = MagicMock()
        mock_stream_obj.text_stream = mock_text_stream()

        class MockCtx:
            async def __aenter__(self):
                return mock_stream_obj
            async def __aexit__(self, *args):
                pass

        mock_client = AsyncMock()
        mock_client.messages.stream = MagicMock(return_value=MockCtx())
        config = {"provider": "Anthropic", "model": "m", "api_key": "k", "base_url": None}

        chunks = []
        async for chunk in llm_stream([(mock_client, config)], "sys", "prompt"):
            chunks.append(chunk)
        assert chunks == ['&&& Paris', '\n### Day 1']

    async def test_stream_fallback(self):
        failing = AsyncMock()
        failing.chat.completions.create.side_effect = Exception("Fail")
        fail_config = {"provider": "DeepSeek", "model": "m", "api_key": "k", "base_url": None}

        async def mock_stream():
            chunk = MagicMock(choices=[MagicMock(delta=MagicMock(content="ok"))])
            yield chunk

        working = AsyncMock()
        working.chat.completions.create.return_value = mock_stream()
        work_config = {"provider": "Moonshot", "model": "m", "api_key": "k", "base_url": None}

        chunks = []
        async for chunk in llm_stream([(failing, fail_config), (working, work_config)], "sys", "prompt"):
            chunks.append(chunk)
        assert chunks == ["ok"]

    async def test_stream_all_fail(self):
        failing = AsyncMock()
        failing.chat.completions.create.side_effect = Exception("Down")
        config = {"provider": "DeepSeek", "model": "m", "api_key": "k", "base_url": None}

        with pytest.raises(RuntimeError, match="All LLM providers failed"):
            async for _ in llm_stream([(failing, config)], "sys", "prompt"):
                pass
