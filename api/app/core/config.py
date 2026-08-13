from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central place for every value that differs between local/staging/production.

    Nothing in the app should read os.environ directly -- it should import `settings`
    from here instead, so there's exactly one place that knows where config comes from.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str
    jwt_access_token_minutes: int = 15
    jwt_refresh_token_days: int = 7
    cors_origins: str = "http://localhost:3000"
    cookie_samesite: str = "lax"
    # Optional: powers AI-generated recommendation explanations in later
    # phases. Get a free key (no card required) at
    # https://console.groq.com/keys.
    groq_api_key: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
