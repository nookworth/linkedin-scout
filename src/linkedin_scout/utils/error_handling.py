"""
Error handling utilities for LinkedIn Scout.
"""
import asyncio
import time
from functools import wraps
from typing import Callable, Any, Dict, Optional, Type, Union, List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .logging_config import get_logger, log_error_with_context


class LinkedInScoutError(Exception):
    """Base exception for LinkedIn Scout application."""
    pass


class AuthenticationError(LinkedInScoutError):
    """Raised when LinkedIn authentication fails."""
    pass


class NavigationError(LinkedInScoutError):
    """Raised when browser navigation fails."""
    pass


class ExtractionError(LinkedInScoutError):
    """Raised when profile data extraction fails."""
    pass


class ExportError(LinkedInScoutError):
    """Raised when result export fails."""
    pass


class RateLimitError(LinkedInScoutError):
    """Raised when LinkedIn rate limiting is detected."""
    pass


class ConfigurationError(LinkedInScoutError):
    """Raised when configuration is invalid."""
    pass


def with_error_handling(
    exceptions: Union[Type[Exception], List[Type[Exception]]] = Exception,
    default_return: Any = None,
    log_level: str = "error",
    context: Optional[Dict[str, Any]] = None
):
    """
    Decorator to add comprehensive error handling to functions.
    
    Args:
        exceptions: Exception types to catch
        default_return: Value to return on error
        log_level: Logging level for errors
        context: Additional context for logging
    """
    if not isinstance(exceptions, list):
        exceptions = [exceptions]
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(f"error_handler.{func.__module__}")
            try:
                return await func(*args, **kwargs)
            except tuple(exceptions) as e:
                error_context = context or {}
                error_context.update({
                    "function": func.__name__,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys())
                })
                
                log_error_with_context(logger, e, error_context)
                
                if default_return is not None:
                    return default_return
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(f"error_handler.{func.__module__}")
            try:
                return func(*args, **kwargs)
            except tuple(exceptions) as e:
                error_context = context or {}
                error_context.update({
                    "function": func.__name__,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys())
                })
                
                log_error_with_context(logger, e, error_context)
                
                if default_return is not None:
                    return default_return
                raise
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def with_retry(
    max_attempts: int = 3,
    wait_seconds: float = 1.0,
    backoff_multiplier: float = 2.0,
    exceptions: Union[Type[Exception], List[Type[Exception]]] = Exception,
    context: Optional[Dict[str, Any]] = None
):
    """
    Decorator to add retry logic with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        wait_seconds: Initial wait time between retries
        backoff_multiplier: Multiplier for exponential backoff
        exceptions: Exception types that trigger retry
        context: Additional context for logging
    """
    if not isinstance(exceptions, list):
        exceptions = [exceptions]
    
    def decorator(func: Callable) -> Callable:
        
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=wait_seconds, multiplier_max=60),
            retry=retry_if_exception_type(tuple(exceptions)),
            reraise=True
        )
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(f"retry.{func.__module__}")
            try:
                return await func(*args, **kwargs)
            except tuple(exceptions) as e:
                error_context = context or {}
                error_context.update({
                    "function": func.__name__,
                    "retry_attempt": True
                })
                logger.warning(f"Retry attempt for {func.__name__}: {str(e)}")
                raise
        
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=wait_seconds, multiplier_max=60),
            retry=retry_if_exception_type(tuple(exceptions)),
            reraise=True
        )
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(f"retry.{func.__module__}")
            try:
                return func(*args, **kwargs)
            except tuple(exceptions) as e:
                error_context = context or {}
                error_context.update({
                    "function": func.__name__,
                    "retry_attempt": True
                })
                logger.warning(f"Retry attempt for {func.__name__}: {str(e)}")
                raise
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def validate_config(config: Dict[str, Any], required_keys: List[str]) -> None:
    """
    Validate configuration dictionary has required keys.
    
    Args:
        config: Configuration dictionary to validate
        required_keys: List of required configuration keys
        
    Raises:
        ConfigurationError: If required keys are missing
    """
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        raise ConfigurationError(f"Missing required configuration keys: {missing_keys}")


def handle_rate_limit(wait_time: int = 30) -> None:
    """
    Handle LinkedIn rate limiting by waiting.
    
    Args:
        wait_time: Time to wait in seconds
    """
    logger = get_logger("rate_limit")
    logger.warning(f"Rate limit detected, waiting {wait_time} seconds")
    time.sleep(wait_time)


class SafeAsyncContextManager:
    """Safe async context manager that handles cleanup even on errors."""
    
    def __init__(self, resource, cleanup_func: Optional[Callable] = None):
        self.resource = resource
        self.cleanup_func = cleanup_func
        self.logger = get_logger("context_manager")
    
    async def __aenter__(self):
        self.logger.debug(f"Entering context for {type(self.resource).__name__}")
        return self.resource
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.logger.debug(f"Exiting context for {type(self.resource).__name__}")
        
        if exc_type:
            self.logger.error(f"Exception in context: {exc_type.__name__}: {exc_val}")
        
        # Perform cleanup
        if self.cleanup_func:
            try:
                if asyncio.iscoroutinefunction(self.cleanup_func):
                    await self.cleanup_func(self.resource)
                else:
                    self.cleanup_func(self.resource)
                self.logger.debug("Context cleanup completed successfully")
            except Exception as cleanup_error:
                self.logger.error(f"Error during cleanup: {str(cleanup_error)}")
        
        # Don't suppress the original exception
        return False


def create_error_summary(errors: List[Exception]) -> Dict[str, Any]:
    """
    Create a summary of multiple errors for reporting.
    
    Args:
        errors: List of exceptions
        
    Returns:
        Dictionary with error summary
    """
    if not errors:
        return {"total_errors": 0}
    
    error_types = {}
    for error in errors:
        error_type = type(error).__name__
        error_types[error_type] = error_types.get(error_type, 0) + 1
    
    return {
        "total_errors": len(errors),
        "error_types": error_types,
        "first_error": str(errors[0]),
        "last_error": str(errors[-1])
    }