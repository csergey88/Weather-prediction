from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str = ""

    OWM_API_KEY: str = ""
    WEATHERAPI_KEY: str = ""
    ACCUWEATHER_KEY: str = ""

    ENABLED_SOURCES: list[str] = ["openweathermap", "weatherapi", "accuweather", "open_meteo"]
    SOURCE_TIMEOUT_S: int = 10
    MIN_SOURCES: int = 2

    MODEL_VERSION: str = "v1"
    MODEL_PATH: str = "models/correction_model_v1.joblib"
    TEMP_STD_THRESHOLD: float = 3.0

    DB_PATH: str = "data/weather.db"
    CACHE_TTL_CURRENT_S: int = 600
    CACHE_TTL_FORECAST_S: int = 10800

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
