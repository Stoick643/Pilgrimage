"""Application configuration via Pydantic Settings — typed, validated at startup."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All config from .env, typed and validated."""

    # LLM providers (at least one required)
    deepseek_api_key: str | None = None
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"

    moonshot_api_key: str | None = None
    moonshot_model: str = "kimi-k2.5"
    moonshot_base_url: str = "https://api.moonshot.cn/v1"

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5"

    # External APIs (optional)
    unsplash_access_key: str | None = None
    openweathermap_api_key: str | None = None
    google_directions_api_key: str | None = None

    # App settings
    active_prompt: str = "detailed"  # "concise" or "detailed"
    streaming_enabled: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def llm_providers(self) -> list[dict[str, str | None]]:
        """Build ordered list of available LLM provider configs."""
        providers = []
        if self.deepseek_api_key:
            providers.append({
                "provider": "DeepSeek",
                "api_key": self.deepseek_api_key,
                "model": self.deepseek_model,
                "base_url": self.deepseek_base_url,
            })
        if self.moonshot_api_key:
            providers.append({
                "provider": "Moonshot",
                "api_key": self.moonshot_api_key,
                "model": self.moonshot_model,
                "base_url": self.moonshot_base_url,
            })
        if self.anthropic_api_key:
            providers.append({
                "provider": "Anthropic",
                "api_key": self.anthropic_api_key,
                "model": self.anthropic_model,
                "base_url": None,
            })
        return providers

    @property
    def unsplash_url(self) -> str:
        return "https://unsplash.com/?utm_source=couch_traveller&utm_medium=referral"


settings = Settings()
