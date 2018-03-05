from functools import wraps

from aiopvapi.helpers.aiorequest import PvApiError

from pv_prompt.print_output import warn


def coro(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            val = self.request.loop.run_until_complete(
                func(self, *args, **kwargs))
            # val = self.loop.run_until_complete(func(self, *args, **kwargs))
            # self.loop.stop()
            return val
        except PvApiError as err:
            warn("PROBLEM SENDING OUT COMMAND.")

    return wrapper
