from pathlib import Path
from loguru import logger
from backend.app.core.config import settings

logger.remove()

LOG_DIR = Path(__file__).parent.parent / "logs"

LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{name}:{function}:{line} | "
    "{message}"
)

logger.add(
    sink=str(LOG_DIR / "debug.log"),
    format=LOG_FORMAT,
    level="DEBUG" if settings.ENVIRONMENT == "development" else "INFO",
    filter=lambda record: record["level"].no <= logger.level("WARNING").no,
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    enqueue=True,
)

logger.add(
    sink=str(LOG_DIR / "error.log"),
    format=LOG_FORMAT,
    level="ERROR",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    backtrace=True,
    diagnose=True,
    enqueue=True,
)


def get_logger():
    return logger
