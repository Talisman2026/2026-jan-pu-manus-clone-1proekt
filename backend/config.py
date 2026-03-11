from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    DATABASE_URL: str

    @property
    def async_database_url(self) -> str:
        """Ensure the URL uses the asyncpg driver for SQLAlchemy async engine."""
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15

    E2B_API_KEY: str
    OPENAI_API_KEY: str
    FIRECRAWL_API_KEY: str

    RESULTS_DIR: str = "./results"


settings = Settings()
