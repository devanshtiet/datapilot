# =============================================================================
# DataPilot — Application Settings
# Loaded via pydantic-settings; all values come from environment variables
# or a .env file. Never hardcode secrets here.
# =============================================================================

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM providers (Mission 2+) ────────────────────────────────────────────
    groq_api_key: str | None = Field(default=None, description="Groq API key")
    openai_api_key: str | None = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI chat model used for narrative insights")
    groq_model: str = Field(default="llama-3.1-8b-instant", description="Groq chat model used for narrative insights")

    llm_provider: Literal["groq", "openai", "auto"] = Field(
        default="auto",
        description=(
            "Which LLM provider to use. 'auto' selects Groq if GROQ_API_KEY is set, "
            "otherwise OpenAI."
        ),
    )

    @property
    def resolved_provider(self) -> Literal["groq", "openai"] | None:
        """Return the concrete provider, resolving 'auto'."""
        if self.llm_provider == "auto":
            if self.groq_api_key:
                return "groq"
            if self.openai_api_key:
                return "openai"
            return None
        return self.llm_provider  # type: ignore[return-value]

    # ── Database (Mission 3+) ─────────────────────────────────────────────────
    database_url: str | None = Field(
        default=None,
        description="PostgreSQL connection string, e.g. postgresql+psycopg2://user:pass@host/db",
    )

    # ── File ingestion ────────────────────────────────────────────────────────
    max_upload_mb: int = Field(
        default=200,
        description="Maximum allowed upload file size in megabytes.",
    )

    @field_validator("max_upload_mb")
    @classmethod
    def _positive_mb(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("max_upload_mb must be a positive integer")
        return v

    # ── Anomaly detection ─────────────────────────────────────────────────────
    isolation_forest_contamination: str | float = Field(
        default="auto",
        description=(
            "Contamination parameter for IsolationForest. "
            "Use 'auto' for sklearn default or a float in (0, 0.5]."
        ),
    )

    @field_validator("isolation_forest_contamination")
    @classmethod
    def _valid_contamination(cls, v: str | float) -> str | float:
        if isinstance(v, str) and v != "auto":
            raise ValueError("isolation_forest_contamination must be 'auto' or a float")
        if isinstance(v, float) and not (0 < v <= 0.5):
            raise ValueError("isolation_forest_contamination float must be in (0, 0.5]")
        return v

    isolation_forest_n_estimators: int = Field(
        default=100,
        description="Number of trees in IsolationForest.",
    )

    isolation_forest_random_state: int = Field(
        default=42,
        description="Random seed for reproducible IsolationForest results.",
    )

    # ── Z-score threshold ─────────────────────────────────────────────────────
    zscore_threshold: float = Field(
        default=3.0,
        description="Absolute Z-score threshold above which a value is flagged.",
    )

    # ── IQR fence multiplier ──────────────────────────────────────────────────
    iqr_fence_multiplier: float = Field(
        default=1.5,
        description="Tukey fence multiplier: fences = Q1 ± k×IQR.",
    )


# Singleton — import this everywhere
settings = Settings()
