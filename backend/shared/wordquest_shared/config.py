from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite:///./wordquest9.db"

    # Security / JWT
    jwt_secret_key: str = "wordquest9-dev-secret-key-change-in-production-64chars-minimum!!"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24h

    # Game Mechanics
    session_question_count: int = 20
    warmup_card_count: int = 6
    mistake_mastery_threshold: int = 2  # 2-3 consecutive correct answers to resolve a mistake

    # Service URLs
    identity_service_url: str = "http://localhost:8001"
    vocabulary_service_url: str = "http://localhost:8002"
    quiz_engine_service_url: str = "http://localhost:8003"
    progress_service_url: str = "http://localhost:8004"
    mcp_server_port: int = 8005

    # Data directory
    data_dir: str = str(Path(__file__).resolve().parents[3] / "data")

    # CORS
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
