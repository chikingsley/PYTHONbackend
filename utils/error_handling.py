import functools
import time
from typing import Callable, Any
import logging

class RetryError(Exception):
    """Custom exception for retry failures"""
    pass

def retry_with_backoff(
    retries: int = 3,
    backoff_in_seconds: int = 1,
    max_backoff: int = 32,
    exceptions: tuple = (Exception,)
) -> Callable:
    """Retry decorator with exponential backoff"""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get logger
            logger = logging.getLogger(func.__module__)
            
            retry_count = 0
            backoff = backoff_in_seconds
            
            while retry_count < retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retry_count += 1
                    if retry_count == retries:
                        logger.error(
                            f"Failed after {retries} retries. Error: {str(e)}"
                        )
                        raise RetryError(
                            f"Maximum retries ({retries}) exceeded."
                        ) from e
                    
                    logger.warning(
                        f"Retry {retry_count}/{retries}. Error: {str(e)}"
                    )
                    time.sleep(backoff)
                    backoff = min(backoff * 2, max_backoff)
            
            return None
        
        return wrapper
    
    return decorator

def handle_api_error(func: Callable) -> Callable:
    """Decorator to handle API errors"""
    
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger = logging.getLogger(func.__module__)
        
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"API Error in {func.__name__}: {str(e)}")
            raise
    
    return wrapper 