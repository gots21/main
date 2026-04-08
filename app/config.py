from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    anthropic_api_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./personality.db"
    chroma_path: str = "./chroma_store"
    claude_model: str = "claude-sonnet-4-6"


settings = Settings()
