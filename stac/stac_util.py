from logging import Logger, FileHandler, StreamHandler, getLogger
from pathlib import Path
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

def get_project_root():
    """
    Gets the project root directory, assuming this function is called
    from a file within the project, and that there's a 'pyproject.toml'
    file at the project root.
    """
    current_file = Path(__file__).resolve()
    # Go up directories until we find 'pyproject.toml'
    for parent in current_file.parents: 
        if (parent / "pyproject.toml").exists():
            return parent
    raise FileNotFoundError("Project root (with pyproject.toml) not found.")