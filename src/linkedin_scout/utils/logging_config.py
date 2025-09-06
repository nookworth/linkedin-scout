"""
Logging configuration for LinkedIn Scout.
"""
import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    log_dir: str = "./logs",
    enable_console: bool = True,
    enable_file: bool = True
) -> logging.Logger:
    """
    Setup centralized logging configuration for LinkedIn Scout.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Specific log file name (defaults to timestamped file)
        log_dir: Directory for log files
        enable_console: Whether to log to console
        enable_file: Whether to log to file
        
    Returns:
        Configured logger instance
    """
    # Create log directory
    Path(log_dir).mkdir(exist_ok=True)
    
    # Set log level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create root logger
    logger = logging.getLogger("linkedin_scout")
    logger.setLevel(numeric_level)
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if enable_file:
        if not log_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"linkedin_scout_{timestamp}.log"
        
        log_path = Path(log_dir) / log_file
        
        # Use rotating file handler to prevent huge log files
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    logger.info(f"Logging initialized - Level: {level}, Console: {enable_console}, File: {enable_file}")
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Module name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f"linkedin_scout.{name}")


def log_function_entry(logger: logging.Logger, func_name: str, **kwargs):
    """Helper to log function entry with parameters."""
    params = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.debug(f"Entering {func_name}({params})")


def log_function_exit(logger: logging.Logger, func_name: str, result=None):
    """Helper to log function exit with result."""
    if result is not None:
        logger.debug(f"Exiting {func_name} -> {type(result).__name__}")
    else:
        logger.debug(f"Exiting {func_name}")


def log_error_with_context(logger: logging.Logger, error: Exception, context: dict = None):
    """
    Log an error with additional context information.
    
    Args:
        logger: Logger instance
        error: Exception to log
        context: Additional context dictionary
    """
    error_msg = f"Error: {type(error).__name__}: {str(error)}"
    
    if context:
        context_str = ", ".join([f"{k}={v}" for k, v in context.items()])
        error_msg += f" | Context: {context_str}"
    
    logger.error(error_msg, exc_info=True)