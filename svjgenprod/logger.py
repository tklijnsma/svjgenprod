import logging
from termcolor import colored

formatter = logging.Formatter(
    fmt = colored('[svj|%(levelname)s|%(asctime)s|%(module)s]:', 'yellow') + ' %(message)s'
    )

def setup_logger(name):
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger


subprocess_formatter = logging.Formatter(fmt = colored('[subprocess]:', 'red') + ' %(message)s')

def setup_subprocess_logger(name):
    handler = logging.StreamHandler()
    handler.setFormatter(subprocess_formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger
