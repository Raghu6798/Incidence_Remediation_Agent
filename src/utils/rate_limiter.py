from tenacity import (
    retry,
    retry_if_exception,
    wait_random_exponential,
    stop_after_delay,
    stop_after_attempt,
    RetryError,
    before_sleep_log,
)
import logging


logging.basicConfig(stream=logging.StreamHandler(), level=logging.INFO)
TENACITY_LOGGER = logging.getLogger(__name__)


retry_with_logging = retry(
    # Wait for an exponentially increasing random time between retries,
    # starting from 1 second, up to a maximum of 60 seconds.
    wait=wait_random_exponential(multiplier=1, max=60),
    # Stop retrying after 3 attempts.
    stop=stop_after_attempt(3),
    # Log before sleeping between retries.
    before_sleep=before_sleep_log(TENACITY_LOGGER, logging.WARNING),
    # You can specify which exceptions should trigger a retry.
    # By default, it retries on any Exception.
    # retry=retry_if_exception_type(IOError)
)