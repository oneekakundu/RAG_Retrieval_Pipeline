import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


def ensure_directory(path: os.PathLike | str) -> Path:
    """Create a directory and return it as a Path object."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def setup_logger(name: str, log_file: Optional[os.PathLike | str] = None) -> logging.Logger:
    """Create a configured logger that writes to console and optional file."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        if log_file:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger


def safe_json_dump(data: Dict[str, Any], path: os.PathLike | str) -> None:
    """Write JSON data to disk atomically-like with pretty formatting."""
    path = Path(path)
    ensure_directory(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)


def read_json(path: os.PathLike | str) -> Any:
    """Read JSON data from disk."""
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def clean_filename(name: str) -> str:
    """Return a filesystem-safe filename."""
    invalid_chars = "<>:/\\|?*\""
    for char in invalid_chars:
        name = name.replace(char, "-")
    return name[:180].strip() or "document"
