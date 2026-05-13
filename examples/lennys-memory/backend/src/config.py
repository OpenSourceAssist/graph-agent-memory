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

    # Neo4j Configuration
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_username: str = Field(default="neo4j")
    neo4j_password: SecretStr = Field(default=SecretStr("password"))

    # OpenAI Configuration
    openai_api_key: SecretStr = Field(default=SecretStr(""))

    # Provider Configuration (v0.3+)
    # Override these to swap LLM/embedding provider without touching code.
    # Defaults preserve the v0.2 behaviour (OpenAI for both); set to e.g.
    # ``"anthropic/claude-3-5-sonnet-latest"`` and
    # ``"BAAI/bge-small-en-v1.5"`` to run on Anthropic + local embeddings.
    llm_model: str = Field(
        default="openai/gpt-4o-mini",
        description="LLM provider string for entity extraction.",
    )
    embedding_model: str = Field(
        default="openai/text-embedding-3-small",
        description="Embedding provider string. Use sentence-transformers IDs (e.g. 'BAAI/bge-small-en-v1.5') for local embeddings.",
    )
    anthropic_api_key: SecretStr | None = Field(
        default=None,
        description="Required when llm_model targets Anthropic.",
    )

    # Enrichment Configuration
    enrichment_enabled: bool = Field(default=True)  # Enable Wikipedia enrichment
    diffbot_api_key: SecretStr | None = Field(default=None)  # Optional Diffbot API key

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
