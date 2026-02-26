import logging
import time
from functools import wraps


logger = logging.getLogger(__name__)


class TransientError(Exception):
    pass


def with_retry(max_attempts: int = 3, base_delay: int = 1, max_delay: int = 60):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except TransientError:
                    if attempt == max_attempts - 1:
                        raise
                    delay = min(base_delay * (2**attempt), max_delay)
                    logger.warning("Attempt %s failed, retrying in %ss", attempt + 1, delay)
                    time.sleep(delay)

        return wrapper

    return decorator
