import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "sqlite:///./classified_ads.db"
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    environment: str = "development"
    upload_dir: str = "uploads"
    max_upload_size: int = 10485760
    allowed_image_types: str = "image/jpeg,image/png,image/webp"

    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v):
        if not v or v == "your-secret-key-change-in-production":
            raise ValueError("secret_key must be set in .env and >= 32 chars")
        if len(v) < 32:
            raise ValueError("secret_key must be at least 32 characters")
        return v

    @field_validator('algorithm')
    @classmethod
    def validate_algorithm(cls, v):
        if v not in ["HS256", "HS384", "HS512", "RS256"]:
            raise ValueError(f"algorithm must be HS256/HS384/HS512/RS256, got {v}")
        return v

    @field_validator('access_token_expire_minutes')
    @classmethod
    def validate_expiry(cls, v):
        if v <= 0:
            raise ValueError("access_token_expire_minutes must be > 0")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings():
    return Settings()