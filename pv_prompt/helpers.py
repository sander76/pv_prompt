import asyncio
import logging

LOGGER = logging.getLogger(__name__)
_LOOP = None

_VERBOSE = False


@property
def VERBOSE():
    return _VERBOSE


def set_verbosity(verbose=True):
    global _VERBOSE
    _VERBOSE = verbose
    LOGGER.debug("Verbose: %s", _VERBOSE)


def get_loop():
    """Return a default asyncio event loop."""
    global _LOOP

    if _LOOP is not None:
        return _LOOP

    _LOOP = asyncio.get_event_loop()
    return _LOOP
