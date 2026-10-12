import sys
from pathlib import Path

from loguru import logger


def setup_logger(log_dir: Path, level: str = "INFO"):
    """Configure console and rotating file logging."""
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.remove()

    log_format = (
        "<green>{time}</green> | "
        "<cyan>{file.name}:{line}</cyan> | "
        "{level} | {message} | {extra}"
    )

    logger.add(
        sys.stderr,
        format=log_format,
        level=level.upper(),
    )

    logger.add(
        log_dir / "greenmiles.log",
        format=log_format,
        level=level.upper(),
        rotation="10 MB",
        retention="10 days",
        compression="zip",
        enqueue=True,
    )

    return logger
