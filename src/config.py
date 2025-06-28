"""
Configuration module for AutoGKB.

This module handles debug mode configuration and logging setup.
"""

from loguru import logger
from typing import NoReturn
import sys

# Global debug flag
DEBUG: bool = False

if DEBUG:
    logger.debug("Debug mode is enabled")


def set_debug(debug: bool) -> NoReturn:
    """
    Set the debug mode globally.
    
    Args:
        debug: Boolean flag to enable/disable debug mode
    """
    global DEBUG
    DEBUG = debug
    
    if DEBUG:
        logger.debug("Debug mode enabled")
    else:
        logger.debug("Debug mode disabled")


def save_logs(save: bool = False) -> NoReturn:
    """
    Configure logging to save logs to a file.
    
    Args:
        save: Boolean flag to enable/disable log file saving (default: False)
    """
    if save:
        # Remove default console handler and add file handler
        logger.remove()
        logger.add(
            "autogkb.log",
            rotation="10 MB",
            retention="7 days",
            level="DEBUG"
        )
        logger.info("Logs will be saved to autogkb.log")
    else:
        # Remove all handlers and add back console handler
        logger.remove()
        logger.add(sys.stderr, level="INFO")
        logger.info("Logs will be output to console only")