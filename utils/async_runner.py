import asyncio
import threading
import traceback  # Added this import
from typing import Any, Callable, Optional


def run_async_in_thread(
    async_func: Callable[..., Any],
    *args: Any,
    callback: Optional[Callable[[Any], None]] = None,
    **kwargs: Any,
) -> threading.Thread:
    """
    Runs an asynchronous function in a new background thread.

    Args:
        async_func: The asynchronous function to run.
        *args: Positional arguments to pass to the async function.
        callback: An optional callback function to execute with the result
                  of the async function once it completes.
        **kwargs: Keyword arguments to pass to the async function.

    Returns:
        The threading.Thread object.
    """

    def task():
        try:
            result = asyncio.run(async_func(*args, **kwargs))
            if callback:
                callback(result)
        except Exception as e:
            if callback:
                callback({"error": str(e), "traceback": traceback.format_exc()})
            else:
                # Log the error if no callback is provided to handle it
                import logging

                logging.error(f"Error in background async task: {e}", exc_info=True)

    thread = threading.Thread(target=task)
    thread.start()
    return thread
