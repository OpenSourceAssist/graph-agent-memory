"""Configuration for Google Cloud Financial Advisor.

This module provides settings management for the application using Pydantic Settings.
Configuration can be provided via environment variables or a .env file.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Annotated

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class VertexAISettings(BaseSettings):
    """Vertex AI configuration for LLM and embeddings."""

    model_config = SettingsConfigDict(
        env_prefix="VERTEX_AI_",
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    project_id: str | None = Field(
        default=None,
        description="Google Cloud Project ID. Falls back to GOOGLE_CLOUD_PROJECT.",
    )
    location: str = Field(
        default="us-central1",
        description="Google Cloud region for Vertex AI",
    )
    model_id: str = Field(
        default="gemini-2.5-flash",
        description="Gemini model for agent reasoning",
    )
    embedding_model: str = Field(
        default="text-embedding-004",
        description="Vertex AI embedding model",
    )

    def get_project_id(self) -> str:
        """Get the project ID, falling back to GOOGLE_CLOUD_PROJECT."""
        if self.project_id:
            return self.project_id
        return os.environ.get("GOOGLE_CLOUD_PROJECT", "")


class Neo4jSettings(BaseSettings):
    """Neo4j Aura configuration."""

    model_config = SettingsConfigDict(
        env_prefix="NEO4J_",
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j connection URI",
    )
    user: str = Field(
        default="neo4j",
        description="Neo4j username",
    )
    password: SecretStr = Field(
        default=SecretStr("password"),
        description="Neo4j password",
    )
    database: str = Field(
        default="neo4j",
        description="Neo4j database name",
    )


class GCSSettings(BaseSettings):
    """Cloud Storage configuration for documents."""

    model_config = SettingsConfigDict(env_prefix="GCS_")

    bucket_name: str = Field(
        default="financial-advisor-documents",
        description="GCS bucket for document storage",
    )


class Settings(BaseSettings):
    """Main application settings.

    Load configuration from environment variables and .env file.
    Nested settings are loaded from prefixed environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Nested settings
    vertex_ai: Annotated[VertexAISettings, Field(default_factory=VertexAISettings)]
    neo4j: Annotated[Neo4jSettings, Field(default_factory=Neo4jSettings)]
    gcs: Annotated[GCSSettings, Field(default_factory=GCSSettings)]

    # Application settings
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )
    cors_origins: str = Field(
        default="http://localhost:5173",
        description="Comma-separated list of allowed CORS origins",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )

    def get_cors_origins_list(self) -> list[str]:
        """Parse CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Singleton Settings instance.
    """
    return Settings()
