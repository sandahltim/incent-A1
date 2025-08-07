import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging():
    """Configure root logging with console and rotating file handlers.

    This function is safe to call multiple times; configuration only
    occurs on the first call when no handlers are attached to the root
    logger.
    """
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s:%(name)s:%(message)s"
    )

    file_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=3)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.DEBUG)

    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)
