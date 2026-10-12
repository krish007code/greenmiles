import configparser
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


class LoggingConfig(BaseModel):
    level: Literal["TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    directory: str = "utility/logs"


class RoutingConfig(BaseModel):
    default_pace_min_per_km: float = Field(default=6.0, gt=0)
    max_candidates: int = Field(default=3, ge=1, le=20)


class AppConfig(BaseModel):
    name: str = "GreenMiles"
    environment: str = "development"
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    routing: RoutingConfig = Field(default_factory=RoutingConfig)


def load_config(config_path: Path | None = None) -> AppConfig:
    """Read the INI file, apply environment overrides, and validate."""
    path = config_path or PROJECT_ROOT / "config" / "app.ini"

    parser = configparser.ConfigParser()

    if not path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with path.open(encoding="utf-8") as file:
        parser.read_file(file)

    raw = {
        "name": parser.get("application", "name"),
        "environment": os.getenv(
            "GREENMILES_ENV",
            parser.get("application", "environment"),
        ),
        "logging": {
            "level": os.getenv(
                "GREENMILES_LOG_LEVEL",
                parser.get("logging", "level"),
            ).upper(),
            "directory": parser.get("logging", "directory"),
        },
        "routing": {
            "default_pace_min_per_km": parser.getfloat(
                "routing", "default_pace_min_per_km"
            ),
            "max_candidates": parser.getint("routing", "max_candidates"),
        },
    }

    return AppConfig.model_validate(raw)
