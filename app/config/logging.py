from pathlib import Path

from loguru import logger

# Project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Remove default logger
logger.remove()

# Console Logger
logger.add(
    sink=lambda msg: print(msg, end=""),
    level="DEBUG",
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "{message}"
    ),
)

# File Logger
logger.add(
    LOG_DIR / "app.log",
    level="INFO",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    enqueue=True,
    backtrace=True,
    diagnose=True,
)

__all__ = ["logger"]