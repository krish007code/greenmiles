from pathlib import Path

from greenmiles.utility.custom_logger import setup_logger


def test_setup_logger_creates_log_directory(tmp_path: Path):
    log_dir = tmp_path / "logs"

    configured_logger = setup_logger(log_dir, level="INFO")

    assert log_dir.is_dir()
    assert (log_dir / "greenmiles.log").is_file()

    configured_logger.complete()
