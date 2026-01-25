"""Application configuration settings."""

from functools import lru_cache

from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Neo4j Memory Graph Configuration
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_username: str = Field(default="neo4j")
    neo4j_password: SecretStr = Field(default=SecretStr("password"))

    # Neo4j News Graph Configuration
    news_graph_uri: str = Field(default="bolt://localhost:7687")
    news_graph_username: str = Field(default="neo4j")
    news_graph_password: SecretStr = Field(default=SecretStr("password"))
    news_graph_database: str = Field(default="neo4j")

    # OpenAI Configuration
    openai_api_key: SecretStr = Field(default=SecretStr(""))

    # Server Configuration
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    debug: bool = Field(default=True)
    cors_origins_str: str = Field(default="http://localhost:3000", alias="cors_origins")
    cors_origin_regex: str | None = Field(default=None)

    @computed_field
    @property
    def cors_origins(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins_str.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
