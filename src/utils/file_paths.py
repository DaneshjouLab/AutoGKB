import os
from pathlib import Path


def get_project_root() -> Path:
    """
    Return the project root directory.
    """
    # Assuming src is a top-level directory in the project
    current_file = Path(__file__)
    return current_file.parent.parent.parent
