# app/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Manages all application settings.
    It automatically reads environment variables from a .env file.
    """
    # Database configuration
    database_url: str

    # JWT Authentication configuration
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    

    class Config:
        # This tells pydantic-settings to load variables from a file named .env
        env_file = ".env"

# Create a single, importable instance of the settings
settings = Settings()