#!/usr/bin/env python3
"""
Shared configuration loader for Claude Content Skills
Handles .env files and JSON config files
"""

import os
import json
from pathlib import Path
from typing import Any, Optional
from dotenv import load_dotenv


def load_env(env_path: Optional[Path] = None) -> None:
    """Load environment variables from .env file"""
    if env_path:
        load_dotenv(env_path)
    else:
        # Try to find .env in current dir or parent dirs
        current = Path.cwd()
        for _ in range(5):  # Check up to 5 levels
            env_file = current / ".env"
            if env_file.exists():
                load_dotenv(env_file)
                return
            current = current.parent
        # Fallback to default dotenv behavior
        load_dotenv()


def get_env(key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    """Get environment variable with optional default and required flag"""
    value = os.getenv(key, default)
    if required and value is None:
        raise ValueError(f"Required environment variable '{key}' is not set")
    return value


def load_json_config(config_path: Path) -> dict[str, Any]:
    """Load JSON configuration file"""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def merge_configs(base: dict, override: dict) -> dict:
    """Deep merge two configuration dictionaries"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    return result


class SkillConfig:
    """Base configuration class for skills"""

    def __init__(self, skill_name: str, config_path: Optional[Path] = None):
        self.skill_name = skill_name
        self._config: dict[str, Any] = {}

        # Load environment variables
        load_env()

        # Load JSON config if provided
        if config_path and config_path.exists():
            self._config = load_json_config(config_path)

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value, checking JSON config first, then env vars"""
        # Check nested keys (e.g., "wordpress.url")
        if "." in key:
            parts = key.split(".")
            value = self._config
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    value = None
                    break
            if value is not None:
                return value

        # Check flat key in config
        if key in self._config:
            return self._config[key]

        # Check environment variable (convert key to ENV_VAR format)
        env_key = key.upper().replace(".", "_")
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value

        return default

    def require(self, key: str) -> Any:
        """Get required config value, raise error if not found"""
        value = self.get(key)
        if value is None:
            raise ValueError(f"Required config '{key}' not found for skill '{self.skill_name}'")
        return value
