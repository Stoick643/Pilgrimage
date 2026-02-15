"""Tests for services.py — image fetching, weather, LLM completion, streaming."""

import pytest
from unittest.mock import patch, MagicMock
from src.services import (
    get_image_url,
    get_weather_forecast_5d,
    get_language_name,
    llm_complete,
    llm_stream,
    DEFAULT_DESCRIPTION,
    ERROR_JPG,
)


# --- Unit tests for get_image_url ---

class TestGetImageUrl:

    def test_hardcoded_rome(self):
        url, desc = get_image_url("Rome")
        assert "staticflickr.com" in url
        assert desc['name'] == "Darko Mulej"

    def test_hardcoded_venice(self):
        url, desc = get_image_url("Venice")
        assert "staticflickr.com" in url
        assert desc['company'] == "Flickr"

    @patch('src.services.UNSPLASH_ACCESS_KEY', None)
    def test_no_unsplash_key_returns_fallback(self):
        url, desc = get_image_url("Berlin")
        assert url == ERROR_JPG
        assert desc == DEFAULT_DESCRIPTION

    @patch('src.services.UNSPLASH_ACCESS_KEY', 'fake-key')
    @patch('src.services.requests.get')
    def test_unsplash_success(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'results': [{
                    'urls': {'regular': 'https://unsplash.com/photo.jpg'},
                    'user': {
                        'name': 'Photographer',
                        'links': {'html': 'https://unsplash.com/@photographer'},
                    },
                }]
            }
        )
        url, desc = get_image_url("Berlin")
        assert url == "https://unsplash.com/photo.jpg"
        assert desc['name'] == "Photographer"
        assert desc['company'] == "Unsplash"

    @patch('src.services.UNSPLASH_ACCESS_KEY', 'fake-key')
    @patch('src.services.requests.get')
    def test_unsplash_empty_results(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {'results': []}
        )
        url, desc = get_image_url("Xyznoplace")
        assert url == ERROR_JPG

    @patch('src.services.UNSPLASH_ACCESS_KEY', 'fake-key')
    @patch('src.services.requests.get')
    def test_unsplash_api_error(self, mock_get):
        mock_get.side_effect = Exception("Connection failed")
        url, desc = get_image_url("Berlin")
        assert url == ERROR_JPG

    @patch('src.services.UNSPLASH_ACCESS_KEY', 'fake-key')
    @patch('src.services.requests.get')
    def test_unsplash_non_200(self, mock_get):
        mock_get.return_value = MagicMock(status_code=403)
        url, desc = get_image_url("Berlin")
        assert url == ERROR_JPG


# --- Unit tests for get_weather_forecast_5d ---

class TestGetWeatherForecast5d:

    @patch('src.services.OPENWEATHERMAP_API_KEY', None)
    def test_no_api_key(self):
        result = get_weather_forecast_5d("Paris")
        assert isinstance(result, str)
        assert "not configured" in result

    @patch('src.services.OPENWEATHERMAP_API_KEY', 'fake-key')
    @patch('src.services.requests.get')
    def test_successful_forecast(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'list': [
                    {
                        'dt_txt': '2026-02-15 15:00:00',
                        'main': {'temp': 8.4},
                        'weather': [{'description': 'cloudy', 'icon': '04d'}],
                    },
                    {
                        'dt_txt': '2026-02-15 18:00:00',
                        'main': {'temp': 6.0},
                        'weather': [{'description': 'clear', 'icon': '01n'}],
                    },
                    {
                        'dt_txt': '2026-02-16 15:00:00',
                        'main': {'temp': 12.1},
                        'weather': [{'description': 'sunny', 'icon': '01d'}],
                    },
                ]
            }
        )
        mock_get.return_value.raise_for_status = MagicMock()

        result = get_weather_forecast_5d("Paris")
        assert isinstance(result, list)
        assert len(result) == 2  # Two days at 15:00
        assert result[0]['temperature'] == 8
        assert result[1]['temperature'] == 12
        assert result[0]['date'] == "15.02"

    @patch('src.services.OPENWEATHERMAP_API_KEY', 'fake-key')
    @patch('src.services.requests.get')
    def test_api_request_error(self, mock_get):
        import requests as req
        mock_get.side_effect = req.RequestException("Timeout")
        result = get_weather_forecast_5d("Paris")
        assert isinstance(result, str)
        assert "Error" in result


# --- Unit tests for get_language_name ---

class TestGetLanguageName:

    def test_known_languages(self):
        assert get_language_name("en") == "English"
        assert get_language_name("de") == "German"
        assert get_language_name("it") == "Italian"
        assert get_language_name("sl") == "Slovenian"

    def test_unknown_language_defaults_to_english(self):
        assert get_language_name("xx") == "English"


# --- Unit tests for llm_complete ---

class TestLlmComplete:

    def test_openai_compatible_provider(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Day 1: Visit Rome"))]
        )
        config = {"provider": "DeepSeek", "model": "deepseek-chat", "api_key": "k", "base_url": None}
        result = llm_complete([(mock_client, config)], "system", "user prompt")
        assert "Rome" in result
        mock_client.chat.completions.create.assert_called_once()

    def test_anthropic_provider(self):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text="Day 1: Visit Rome")]
        )
        config = {"provider": "Anthropic", "model": "claude-sonnet-4-5", "api_key": "k", "base_url": None}
        result = llm_complete([(mock_client, config)], "system", "user prompt")
        assert "Rome" in result
        mock_client.messages.create.assert_called_once()

    def test_fallback_on_failure(self):
        """If first provider fails, should try the next one."""
        failing_client = MagicMock()
        failing_client.chat.completions.create.side_effect = Exception("Rate limit")
        failing_config = {"provider": "DeepSeek", "model": "deepseek-chat", "api_key": "k", "base_url": None}

        working_client = MagicMock()
        working_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text="Day 1: Visit Rome via fallback")]
        )
        working_config = {"provider": "Anthropic", "model": "claude-sonnet-4-5", "api_key": "k", "base_url": None}

        result = llm_complete([(failing_client, failing_config), (working_client, working_config)], "system", "prompt")
        assert "fallback" in result

    def test_all_providers_fail_raises(self):
        """If all providers fail, should raise RuntimeError."""
        failing_client = MagicMock()
        failing_client.chat.completions.create.side_effect = Exception("Down")
        config = {"provider": "DeepSeek", "model": "deepseek-chat", "api_key": "k", "base_url": None}

        with pytest.raises(RuntimeError, match="All LLM providers failed"):
            llm_complete([(failing_client, config)], "system", "prompt")


# --- Unit tests for llm_stream ---

class TestLlmStream:

    def test_openai_streaming(self):
        """OpenAI-compatible streaming yields chunks."""
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock(delta=MagicMock(content="&&&Rome\n"))]
        chunk2 = MagicMock()
        chunk2.choices = [MagicMock(delta=MagicMock(content="Visit the Colosseum"))]
        chunk3 = MagicMock()
        chunk3.choices = [MagicMock(delta=MagicMock(content=None))]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = [chunk1, chunk2, chunk3]
        config = {"provider": "DeepSeek", "model": "deepseek-chat", "api_key": "k", "base_url": None}

        chunks = list(llm_stream([(mock_client, config)], "system", "prompt"))
        assert chunks == ["&&&Rome\n", "Visit the Colosseum"]
        mock_client.chat.completions.create.assert_called_once()
        # Verify stream=True was passed
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["stream"] is True

    def test_anthropic_streaming(self):
        """Anthropic streaming yields chunks via text_stream."""
        mock_stream_ctx = MagicMock()
        mock_stream = MagicMock()
        mock_stream.text_stream = iter(["&&&Paris\n", "Visit the Eiffel Tower"])
        mock_stream_ctx.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream_ctx.__exit__ = MagicMock(return_value=False)

        mock_client = MagicMock()
        mock_client.messages.stream.return_value = mock_stream_ctx
        config = {"provider": "Anthropic", "model": "claude-sonnet-4-5", "api_key": "k", "base_url": None}

        chunks = list(llm_stream([(mock_client, config)], "system", "prompt"))
        assert chunks == ["&&&Paris\n", "Visit the Eiffel Tower"]
        mock_client.messages.stream.assert_called_once()

    def test_stream_fallback_on_failure(self):
        """If first provider fails mid-stream, falls back to next."""
        failing_client = MagicMock()
        failing_client.chat.completions.create.side_effect = Exception("Connection reset")
        failing_config = {"provider": "DeepSeek", "model": "deepseek-chat", "api_key": "k", "base_url": None}

        chunk = MagicMock()
        chunk.choices = [MagicMock(delta=MagicMock(content="&&&Rome\nDay 1"))]
        working_client = MagicMock()
        working_client.chat.completions.create.return_value = [chunk]
        working_config = {"provider": "Moonshot", "model": "kimi-k2.5", "api_key": "k", "base_url": None}

        chunks = list(llm_stream(
            [(failing_client, failing_config), (working_client, working_config)],
            "system", "prompt"
        ))
        assert chunks == ["&&&Rome\nDay 1"]

    def test_stream_all_providers_fail(self):
        """If all providers fail, raises RuntimeError."""
        failing_client = MagicMock()
        failing_client.chat.completions.create.side_effect = Exception("Down")
        config = {"provider": "DeepSeek", "model": "deepseek-chat", "api_key": "k", "base_url": None}

        with pytest.raises(RuntimeError, match="All LLM providers failed to stream"):
            list(llm_stream([(failing_client, config)], "system", "prompt"))
