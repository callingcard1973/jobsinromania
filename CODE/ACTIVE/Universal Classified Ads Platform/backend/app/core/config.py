import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")
    database_url: str = "sqlite:///./classified_ads.db"
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    environment: str = "development"
    upload_dir: str = "uploads"
    max_upload_size: int = 10485760
    allowed_image_types: str = "image/jpeg,image/png,image/webp"
    posthog_api_key: str = ""
    posthog_host: str = "https://us.posthog.com"
    posthog_enabled: bool = True
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    ad_publish_price_cents: int = 500
    currency: str = "usd"
    # WordPress integration — push published ads as WP posts
    wp_site_url: str = ""  # e.g. https://interjob.ro
    wp_user: str = ""
    wp_app_password: str = ""
    wp_enabled: bool = False
    wp_default_category_id: int = 0  # WP term ID for "Classifieds"

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


@lru_cache()
def get_settings():
    return Settings()