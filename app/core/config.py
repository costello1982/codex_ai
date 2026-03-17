"""Application configuration."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    app_name: str = "NX-OS VXLAN EVPN Designer"
    app_env: str = "dev"
    log_level: str = "INFO"
    llm_provider: str = "stub"
    llm_model: str = "local-model"
    openai_api_key: str | None = None
    base_dir: Path = Path(__file__).resolve().parents[2]
    data_dir: Path = base_dir / "app" / "data"
    docs_dir: Path = data_dir / "docs"
    vectorstore_dir: Path = data_dir / "vectorstore"
    policies_dir: Path = data_dir / "policies"
    templates_dir: Path = base_dir / "app" / "templates"
    outputs_dir: Path = base_dir / "outputs"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
