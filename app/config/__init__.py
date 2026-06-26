import os
from app.root import ROOT

if os.path.exists(f"{ROOT}/config/config.py"):
    from .config import *
