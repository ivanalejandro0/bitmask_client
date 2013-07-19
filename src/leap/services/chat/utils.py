import logging


def get_log_handler(name):
    level = logging.DEBUG
    # level = logging.WARNING

    # Create logger and formatter
    logger = logging.getLogger(name)
    logger.setLevel(level)
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    logger.addHandler(console)
    logger.debug('Console handler plugged!')

    return logger
