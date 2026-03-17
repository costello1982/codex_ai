"""Logging bootstrap."""
import logging
from app.core.config import settings


def setup_logging() -> None:
    """Configure global logging format and level."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
