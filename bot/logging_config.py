import logging


def setup_logging():
    logger = logging.getLogger("trading_bot")
    logger.setLevel(logging.INFO)

    if not logger.handlers:

        file_handler = logging.FileHandler("trading_bot.log")

        file_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )

        file_handler.setFormatter(file_formatter)

        console_handler = logging.StreamHandler()

        console_formatter = logging.Formatter(
            "%(levelname)s - %(message)s"
        )

        console_handler.setFormatter(console_formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger