#!/usr/bin/env python3
"""
Tenacity-based retry logic for LLM API calls, specifically tailored for Google Gemini.

This module provides a decorator to handle transient errors commonly encountered when
interacting with LLM APIs, such as:
- Rate limit errors (HTTP 429)
- Server-side errors (HTTP 5xx)
- Timeout errors

It uses an exponential backoff with jitter to gracefully retry failed requests.
"""

import logging
from tenacity import (
    retry,
    retry_if_exception,
    wait_random_exponential,
    stop_after_delay,
    before_sleep_log,
)

# It's a good practice to anticipate potential exceptions from the underlying SDK.
# If you have google-api-core installed, you can be more specific.
try:
    from google.api_core import exceptions as google_exceptions
    # Define a tuple of specific, retryable Google API exceptions
    RETRYABLE_GOOGLE_EXCEPTIONS = (
        google_exceptions.ResourceExhausted,  # HTTP 429 Rate limit
        google_exceptions.ServiceUnavailable, # HTTP 503 Server temporarily unavailable
        google_exceptions.InternalServerError, # HTTP 500 Internal server error
        google_exceptions.Aborted,            # Often indicates a concurrency issue
        google_exceptions.DeadlineExceeded,   # Timeout on the server side
    )
    # Define a tuple of exceptions that should NOT be retried
    NON_RETRYABLE_GOOGLE_EXCEPTIONS = (
        google_exceptions.PermissionDenied,   # HTTP 403, API key issue
        google_exceptions.NotFound,           # HTTP 404
        google_exceptions.InvalidArgument,    # HTTP 400, bad request
        google_exceptions.Unauthenticated,    # HTTP 401, bad API key
    )
except ImportError:
    # If the library isn't installed, fall back to a safe default
    RETRYABLE_GOOGLE_EXCEPTIONS = ()
    NON_RETRYABLE_GOOGLE_EXCEPTIONS = ()
    logging.warning("`google-api-core` not found. Specific Google exception handling will be disabled.")


# Setup a logger for this module to see retry attempts
logger = logging.getLogger(__name__)

def is_retryable_exception(e: BaseException) -> bool:
    """
    Determines if an exception is worth retrying.

    This function checks for:
    1. Standard Python TimeoutError.
    2. Specific retryable exceptions from the Google Cloud SDK.
    3. Avoids retrying non-recoverable client errors (like authentication).
    4. As a fallback, checks exception messages for common rate limit text.

    Args:
        e: The exception instance to check.

    Returns:
        True if the exception is retryable, False otherwise.
    """
    # Do not retry non-recoverable Google API errors
    if isinstance(e, NON_RETRYABLE_GOOGLE_EXCEPTIONS):
        logger.warning(f"Encountered non-retryable Google API error: {e}")
        return False

    # Retry known transient Google API errors and standard timeouts
    if isinstance(e, RETRYABLE_GOOGLE_EXCEPTIONS) or isinstance(e, TimeoutError):
        logger.debug(f"Identified retryable exception: {type(e).__name__}")
        return True

    # Fallback for generic exceptions: check for rate limit text in the message
    error_message = str(e).lower()
    if "rate limit" in error_message or "resource has been exhausted" in error_message:
        logger.debug("Identified retryable exception based on error message content.")
        return True

    logger.error(f"Encountered non-retryable exception: {e}")
    return False


# Define the main retry decorator using our custom logic
gemini_llm_retry = retry(
    # Use our custom function to decide whether to retry
    retry=retry_if_exception(is_retryable_exception),

    # Wait for a random exponential time between retries, starting from 1s up to 60s.
    # This adds jitter and prevents thundering herd issues.
    wait=wait_random_exponential(multiplier=1, max=60),

    # Stop retrying after a total of 5 minutes (300 seconds)
    stop=stop_after_delay(300),

    # Log a warning before each retry attempt
    before_sleep=before_sleep_log(logger, logging.WARNING),
)