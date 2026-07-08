from logging import Logger, FileHandler, StreamHandler, getLogger, DEBUG
import sys, traceback

# file_handler = FileHandler(filename="stac.log")
stream_handler = StreamHandler(sys.stdout)

logger: Logger = getLogger("stac")
logger.addHandler(StreamHandler(sys.stdout))
# logger.addHandler(file_handler)
logger.level = DEBUG


def log_info(msg, e: Exception | None = None):
    """
    Log a message and optional exception traceback information.

    If e is provided only traceback frames are logged, avoiding the full
    exception output and reducing the chance of exposing sensitive runtime
    details.


    Args:
        msg: Message to log.
        e: Optional exception.
    """
    logger.info(msg)

    if e:
        # Log traceback frames without emitting the full exception details.
        logger.info(traceback.extract_tb(e.__traceback__))


def log_warn(msg):
    logger.warn(msg)


def log_exception(msg):
    logger.exception(msg)
