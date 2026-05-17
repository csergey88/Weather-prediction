from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from weather_bot.sources.base import SourceTimeoutError, SourceUnavailableError

retry_async = retry(
    retry=retry_if_exception_type((SourceUnavailableError, SourceTimeoutError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True,
)
