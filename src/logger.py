import logging


def get_logger(name: str) -> logging.Logger:
    root_logger = logging.getLogger()

    if not root_logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )

    return logging.getLogger(name)
