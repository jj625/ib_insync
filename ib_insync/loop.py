import asyncio
import logging
import threading

logger = logging.getLogger(__name__)

def getLoop(debug: bool = False):
    """
    Get the currently running asyncio event loop.

    - Inside async context (e.g., FastAPI/Uvicorn): returns active loop.
    - Outside async context (e.g., CLI, tests): returns or creates default loop.
    - Logs diagnostics if `debug=True`.

    Returns:
        asyncio.AbstractEventLoop: The active or default event loop.
    """
    try:
        loop = asyncio.get_running_loop()
        if debug:
            _log_loop_diagnostics(loop, source="running", debug=debug)
        return loop
    except RuntimeError:
        loop = asyncio.get_event_loop()
        if debug:
            logger.warning("[getLoop] No running loop found — using default loop (may differ from FastAPI/Uvicorn loop)")
            _log_loop_diagnostics(loop, source="default", debug=debug)
        return loop

def _log_loop_diagnostics(loop: asyncio.AbstractEventLoop, source: str, debug: bool):
    """
    Log detailed diagnostics about the event loop.

    Args:
        loop: The event loop instance.
        source: 'running' or 'default' — where the loop came from.
        debug: Whether to emit debug-level logs.
    """
    thread_name = threading.current_thread().name
    loop_type = type(loop).__name__
    loop_id = id(loop)
    is_running = loop.is_running()
    is_closed = loop.is_closed()

    logger.info(f"[getLoop] Loop source: {source}")
    logger.info(f"[getLoop] Thread: {thread_name}")
    logger.info(f"[getLoop] Loop type: {loop_type}")
    logger.info(f"[getLoop] Loop ID: {loop_id}")
    logger.info(f"[getLoop] Loop is_running: {is_running}")
    logger.info(f"[getLoop] Loop is_closed: {is_closed}")

    if debug:
        logger.debug(f"[getLoop] Loop repr: {repr(loop)}")