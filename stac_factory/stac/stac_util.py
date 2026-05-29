from logging import Logger, FileHandler, StreamHandler, getLogger
import sys

file_handler = FileHandler(filename='stac.log')
stream_handler = StreamHandler(sys.stdout)

logger: Logger = getLogger("stac")
logger.addHandler(StreamHandler(sys.stdout))
logger.addHandler(file_handler)

def log_info(msg):
    print(f"msg: {msg}")
    logger.info(msg)

def log_exception(msg):
    print(f"exception: {msg}")
    logger.exception(msg)
