"""Tests for services/llm.py — LLM completion, streaming, prompt building."""

import json
import pytest
from unittest.mock import MagicMock

from v2.services.llm import (
    build_prompt,
    get_language_name,
    llm_complete,
    llm_stream,
    load_prompt,
    _parse_json_response,
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
        assert "JSON" in text

    def test_load_concise(self):
        text = load_prompt("concise")
        assert "{duration}" in text

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
        assert "IMPORTANT" not in user

    def test_max_tokens_capped(self):
        _, _, max_tokens = build_prompt("detailed", 20, "Europe", "all")
        assert max_tokens == 4000  # capped


class TestParseJsonResponse:

    def test_plain_json(self):
        result = _parse_json_response('{"days": []}')
        assert result == {"days": []}

    def test_json_with_code_fence(self):
        raw = '```json\n{"days": []}\n```'
        result = _parse_json_response(raw)
        assert result == {"days": []}

    def test_json_with_whitespace(self):
        result = _parse_json_response('  \n {"days": []} \n  ')
        assert result == {"days": []}

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_json_response("not json at all")


class TestLlmComplete:

    def test_openai_provider_json_mode(self):
        """OpenAI-compatible provider should use response_format json_object."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"days": [{"day": 1, "city": "Rome"}]}'))]
        )
        config = {"provider": "DeepSeek", "model": "deepseek-chat", "api_key": "k", "base_url": None}

        result = llm_complete([(mock_client, config)], "system", "prompt")
        assert result["days"][0]["city"] == "Rome"

        # Verify json_object format was requested
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["response_format"] == {"type": "json_object"}

    def test_anthropic_provider(self):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text='{"days": [{"day": 1, "city": "Paris"}]}')]
        )
        config = {"provider": "Anthropic", "model": "claude-sonnet-4-5", "api_key": "k", "base_url": None}

        result = llm_complete([(mock_client, config)], "system", "prompt")
        assert result["days"][0]["city"] == "Paris"

    def test_fallback_on_failure(self):
        failing = MagicMock()
        failing.chat.completions.create.side_effect = Exception("Rate limit")
        fail_config = {"provider": "DeepSeek", "model": "m", "api_key": "k", "base_url": None}

        working = MagicMock()
        working.messages.create.return_value = MagicMock(
            content=[MagicMock(text='{"days": [{"day": 1, "city": "Fallback"}]}')]
        )
        work_config = {"provider": "Anthropic", "model": "m", "api_key": "k", "base_url": None}

        result = llm_complete([(failing, fail_config), (working, work_config)], "sys", "prompt")
        assert result["days"][0]["city"] == "Fallback"

    def test_all_fail_raises(self):
        failing = MagicMock()
        failing.chat.completions.create.side_effect = Exception("Down")
        config = {"provider": "DeepSeek", "model": "m", "api_key": "k", "base_url": None}

        with pytest.raises(RuntimeError, match="All LLM providers failed"):
            llm_complete([(failing, config)], "sys", "prompt")

    def test_handles_code_fence_response(self):
        """LLM wrapping JSON in markdown fences should still parse."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='```json\n{"days": [{"day": 1, "city": "Tokyo"}]}\n```'
            ))]
        )
        config = {"provider": "DeepSeek", "model": "m", "api_key": "k", "base_url": None}

        result = llm_complete([(mock_client, config)], "sys", "prompt")
        assert result["days"][0]["city"] == "Tokyo"


class TestLlmStream:

    def test_openai_streaming(self):
        chunk1 = MagicMock(choices=[MagicMock(delta=MagicMock(content='{"days"'))])
        chunk2 = MagicMock(choices=[MagicMock(delta=MagicMock(content=': []}'))])
        chunk3 = MagicMock(choices=[MagicMock(delta=MagicMock(content=None))])

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = [chunk1, chunk2, chunk3]
        config = {"provider": "DeepSeek", "model": "m", "api_key": "k", "base_url": None}

        chunks = list(llm_stream([(mock_client, config)], "sys", "prompt"))
        assert chunks == ['{"days"', ': []}']

    def test_anthropic_streaming(self):
        mock_ctx = MagicMock()
        mock_stream = MagicMock()
        mock_stream.text_stream = iter(['{"days"', ': []}'])
        mock_ctx.__enter__ = MagicMock(return_value=mock_stream)
        mock_ctx.__exit__ = MagicMock(return_value=False)

        mock_client = MagicMock()
        mock_client.messages.stream.return_value = mock_ctx
        config = {"provider": "Anthropic", "model": "m", "api_key": "k", "base_url": None}

        chunks = list(llm_stream([(mock_client, config)], "sys", "prompt"))
        assert chunks == ['{"days"', ': []}']

    def test_stream_fallback(self):
        failing = MagicMock()
        failing.chat.completions.create.side_effect = Exception("Fail")
        fail_config = {"provider": "DeepSeek", "model": "m", "api_key": "k", "base_url": None}

        chunk = MagicMock(choices=[MagicMock(delta=MagicMock(content="ok"))])
        working = MagicMock()
        working.chat.completions.create.return_value = [chunk]
        work_config = {"provider": "Moonshot", "model": "m", "api_key": "k", "base_url": None}

        chunks = list(llm_stream([(failing, fail_config), (working, work_config)], "sys", "prompt"))
        assert chunks == ["ok"]

    def test_stream_all_fail(self):
        failing = MagicMock()
        failing.chat.completions.create.side_effect = Exception("Down")
        config = {"provider": "DeepSeek", "model": "m", "api_key": "k", "base_url": None}

        with pytest.raises(RuntimeError, match="All LLM providers failed"):
            list(llm_stream([(failing, config)], "sys", "prompt"))
