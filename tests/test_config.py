import pytest
from pydantic import ValidationError

from greenmiles.config import AppConfig, load_config


def test_load_config():
    config = load_config()

    assert config.name == "GreenMiles"
    assert config.logging.level == "INFO"
    assert config.routing.default_pace_min_per_km > 0


def test_invalid_pace_is_rejected():
    with pytest.raises(ValidationError):
        AppConfig(
            routing={
                "default_pace_min_per_km": 0,
                "max_candidates": 3,
            }
        )
