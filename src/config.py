"""Configuration management using Pydantic Settings."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration from environment variables."""

    # Telegram
    telegram_bot_token: str
    telegram_webhook_url: str
    telegram_webhook_secret: str

    # Poe.com API (OpenAI-compatible)
    poe_api_base_url: str = "https://api.poe.com/v1"
    poe_api_key: str
    poe_model_name: str = "gemini-2-flash"

    # Notion MCP
    notion_api_key: str
    notion_mcp_url: str = "http://notion-mcp:3000"
    notion_mcp_auth_token: str
    
    # Home Assistant Integration (optional)
    home_assistant_url: str = ""
    home_assistant_token: str = ""
    # ha_mcp_url: direct URL to ha-mcp server (POST-only, no SSE)
    # e.g. https://homephi.duckdns.org:8123/api/mcp
    ha_mcp_url: str = ""

    # App settings
    session_ttl_minutes: int = 15

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()  # type: ignore


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings
