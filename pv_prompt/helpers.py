import asyncio

_LOOP = None


def get_loop():
    """Return a default asyncio event loop."""
    global _LOOP

    if _LOOP is not None:
        return _LOOP

    _LOOP = asyncio.get_event_loop()
    return _LOOP
