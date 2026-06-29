from logging import Logger, FileHandler, StreamHandler, getLogger, DEBUG
import sys

file_handler = FileHandler(filename="stac.log")
stream_handler = StreamHandler(sys.stdout)

logger: Logger = getLogger("stac")
logger.addHandler(StreamHandler(sys.stdout))
logger.addHandler(file_handler)
logger.level = DEBUG


def log_info(msg):
    logger.info(msg)


def log_warn(msg):
    logger.warn(msg)


def log_exception(msg):
    logger.exception(msg)
