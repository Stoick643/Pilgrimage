"""Tests for config.py — Pydantic Settings."""

import pytest
from v3.config import Settings


class TestSettings:

    def test_defaults(self):
        """Settings should have sensible defaults when no env/file."""
        s = Settings(
            _env_file=None,  # Don't read .env file
            deepseek_api_key=None,
            moonshot_api_key=None,
            anthropic_api_key=None,
            unsplash_access_key=None,
            openweathermap_api_key=None,
            google_directions_api_key=None,
        )
        assert s.deepseek_api_key is None
        assert s.deepseek_model == "deepseek-chat"
        assert s.streaming_enabled is True
        assert s.active_prompt == "detailed"

    def test_llm_providers_empty_when_no_keys(self):
        s = Settings(
            _env_file=None,
            deepseek_api_key=None,
            moonshot_api_key=None,
            anthropic_api_key=None,
        )
        assert s.llm_providers == []

    def test_llm_providers_with_deepseek(self):
        s = Settings(
            _env_file=None,
            deepseek_api_key="sk-test",
            moonshot_api_key=None,
            anthropic_api_key=None,
        )
        providers = s.llm_providers
        assert len(providers) == 1
        assert providers[0]["provider"] == "DeepSeek"
        assert providers[0]["api_key"] == "sk-test"
        assert providers[0]["model"] == "deepseek-chat"

    def test_llm_providers_priority_order(self):
        s = Settings(
            _env_file=None,
            deepseek_api_key="sk-ds",
            moonshot_api_key="sk-moon",
            anthropic_api_key="sk-ant",
        )
        providers = s.llm_providers
        assert len(providers) == 3
        assert providers[0]["provider"] == "DeepSeek"
        assert providers[1]["provider"] == "Moonshot"
        assert providers[2]["provider"] == "Anthropic"

    def test_custom_models(self):
        s = Settings(
            _env_file=None,
            deepseek_api_key="sk-test",
            deepseek_model="deepseek-v3",
            moonshot_api_key=None,
            anthropic_api_key=None,
        )
        assert s.llm_providers[0]["model"] == "deepseek-v3"

    def test_unsplash_url(self):
        s = Settings(_env_file=None)
        assert "unsplash.com" in s.unsplash_url

    def test_reads_env_file(self):
        """The default singleton should read from .env (integration test)."""
        from v3.config import settings
        # If .env exists with keys, they should be loaded
        # This just verifies the singleton works without error
        assert isinstance(settings.streaming_enabled, bool)
