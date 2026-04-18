"""
Configuration management for European Employer ANOFM Job Fair Integration System.

This module handles all configuration settings including database connections,
API configurations, GDPR compliance settings, and system limits.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseSettings):
    """Database connection configuration."""

    # Local SQLite database
    sqlite_path: str = Field(default="data/jobfairs.db", env="SQLITE_PATH")

    # Master PostgreSQL database on raspibig
    postgres_host: str = Field(default="192.168.100.21", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_database: str = Field(default="interjob_master", env="POSTGRES_DATABASE")
    postgres_user: str = Field(default="tudor", env="POSTGRES_USER")
    postgres_password: str = Field(default="tudor", env="POSTGRES_PASSWORD")

    @property
    def sqlite_url(self) -> str:
        """Get SQLite connection URL."""
        return f"sqlite:///{self.sqlite_path}"

    @property
    def postgres_url(self) -> str:
        """Get PostgreSQL connection URL."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"


class EmailConfig(BaseSettings):
    """Email API configuration for Brevo integration."""

    brevo_api_key: str = Field(default="", env="BREVO_API_KEY")
    brevo_sender_email: str = Field(default="noreply@interjob.ro", env="BREVO_SENDER_EMAIL")
    brevo_sender_name: str = Field(default="InterJob Romania", env="BREVO_SENDER_NAME")
    daily_email_limit: int = Field(default=500, env="DAILY_EMAIL_LIMIT")

    # Campaign-specific limits
    pilot_daily_limit: int = Field(default=50, env="PILOT_DAILY_LIMIT")
    scaling_daily_limit: int = Field(default=200, env="SCALING_DAILY_LIMIT")


class GDPRConfig(BaseSettings):
    """GDPR compliance configuration."""

    # Data retention periods (in days)
    worker_data_retention_days: int = Field(default=1095, env="WORKER_DATA_RETENTION_DAYS")  # 3 years
    employer_data_retention_days: int = Field(default=2555, env="EMPLOYER_DATA_RETENTION_DAYS")  # 7 years
    communication_retention_days: int = Field(default=1095, env="COMMUNICATION_RETENTION_DAYS")  # 3 years

    # Data processor information
    data_controller: str = Field(default="InterJob Romania", env="DATA_CONTROLLER")
    data_controller_address: str = Field(
        default="Bucharest, Romania",
        env="DATA_CONTROLLER_ADDRESS"
    )
    data_processor: str = Field(default="InterJob Romania", env="DATA_PROCESSOR")
    privacy_policy_url: str = Field(
        default="https://interjob.ro/privacy.html",
        env="PRIVACY_POLICY_URL"
    )


class ANOFMConfig(BaseSettings):
    """ANOFM website monitoring configuration."""

    base_url: str = Field(default="https://www.anofm.ro", env="ANOFM_BASE_URL")
    job_fairs_path: str = Field(default="/burse-de-munca", env="ANOFM_JOB_FAIRS_PATH")
    check_interval_hours: int = Field(default=6, env="ANOFM_CHECK_INTERVAL_HOURS")

    # Target regions for monitoring
    target_regions: List[str] = Field(
        default=["Hunedoara", "Gorj", "Vaslui"],
        env="TARGET_REGIONS"
    )


class SystemLimitsConfig(BaseSettings):
    """System operational limits for phased deployment."""

    # Pilot phase limits
    pilot_max_employers: int = Field(default=1, env="PILOT_MAX_EMPLOYERS")
    pilot_max_workers: int = Field(default=10, env="PILOT_MAX_WORKERS")
    pilot_duration_days: int = Field(default=30, env="PILOT_DURATION_DAYS")

    # Scaling phase limits
    scaling_max_employers: int = Field(default=5, env="SCALING_MAX_EMPLOYERS")
    scaling_max_workers: int = Field(default=50, env="SCALING_MAX_WORKERS")
    scaling_duration_days: int = Field(default=60, env="SCALING_DURATION_DAYS")

    # Full deployment limits
    full_max_employers: int = Field(default=50, env="FULL_MAX_EMPLOYERS")
    full_max_workers: int = Field(default=500, env="FULL_MAX_WORKERS")


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="logs/jobfairs.log", env="LOG_FILE")
    log_max_bytes: int = Field(default=10485760, env="LOG_MAX_BYTES")  # 10MB
    log_backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")


class Config(BaseSettings):
    """Main configuration class combining all settings."""

    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")

    # Sub-configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    email: EmailConfig = Field(default_factory=EmailConfig)
    gdpr: GDPRConfig = Field(default_factory=GDPRConfig)
    anofm: ANOFMConfig = Field(default_factory=ANOFMConfig)
    limits: SystemLimitsConfig = Field(default_factory=SystemLimitsConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment setting."""
        valid_envs = ["development", "staging", "production"]
        if v not in valid_envs:
            raise ValueError(f"Environment must be one of: {valid_envs}")
        return v

    def get_current_phase(self) -> str:
        """Determine current deployment phase based on data in system."""
        # This will be implemented to check database for current state
        return "pilot"  # Default to pilot phase

    def get_phase_limits(self, phase: str) -> Dict[str, int]:
        """Get limits for specified phase."""
        if phase == "pilot":
            return {
                "max_employers": self.limits.pilot_max_employers,
                "max_workers": self.limits.pilot_max_workers,
                "daily_emails": self.email.pilot_daily_limit
            }
        elif phase == "scaling":
            return {
                "max_employers": self.limits.scaling_max_employers,
                "max_workers": self.limits.scaling_max_workers,
                "daily_emails": self.email.scaling_daily_limit
            }
        else:  # full
            return {
                "max_employers": self.limits.full_max_employers,
                "max_workers": self.limits.full_max_workers,
                "daily_emails": self.email.daily_email_limit
            }


# Global config instance
config = Config()


def get_config() -> Config:
    """Get the global configuration instance."""
    return config


def reload_config() -> Config:
    """Reload configuration from environment."""
    global config
    config = Config()
    return config