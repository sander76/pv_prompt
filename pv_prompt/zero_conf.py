""" Example of browsing for a service (in this case, HTTP) """

import asyncio
import logging
import socket

from aiopvapi.helpers.aiorequest import AioRequest
from aiopvapi.hub import Hub
from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange

LOGGER = logging.getLogger(__name__)


class Zero:
    def __init__(self, loop):
        self.hubs = []
        self._zeroconf = Zeroconf()
        self.browser = None
        self._loop = loop
        self._tasks = []

    async def add_update_task(self, hub):
        await hub.query_user_data()
        await hub.request.websession.close()

    async def discover(self, wait_for=5):
        LOGGER.debug('starting discovery')
        self.browser = ServiceBrowser(
            self._zeroconf, "_powerview._tcp.local.",
            handlers=[self.on_service_state_change])

        LOGGER.debug("waiting for {} seconds".format(wait_for))
        await asyncio.sleep(wait_for)

        LOGGER.debug("closing discovery")
        self._zeroconf.close()

        LOGGER.debug("waiting for all tasks to finish.")
        try:
            await asyncio.gather(*self._tasks)
        except Exception as err:
            LOGGER.exception(err)

    def on_service_state_change(self, zeroconf, service_type, name,
                                state_change):
        LOGGER.debug("Service %s of type %s state changed: %s" % (
            name, service_type, state_change))

        if state_change is ServiceStateChange.Added:
            info = zeroconf.get_service_info(service_type, name)
            if info:
                address = socket.inet_ntoa(info.address)
                LOGGER.debug("hub found with ip: {}".format(address))
                request = AioRequest(hub_ip=address, loop=self._loop)
                hub = Hub(request)
                self.hubs.append(hub)
                self._tasks.append(
                    self._loop.create_task(self.add_update_task(hub)))

# if __name__ == '__main__':
#     z = Zero()
#     z.discover()
#     # logging.basicConfig(level=logging.DEBUG)
#     # if len(sys.argv) > 1:
#     #     assert sys.argv[1:] == ['--debug']
#     #     logging.getLogger('zeroconf').setLevel(logging.DEBUG)
#     #
#     # zeroconf = Zeroconf()
#     # print("\nBrowsing services, press Ctrl-C to exit...\n")
#     # browser = ServiceBrowser(zeroconf, "_powerview._tcp.local.",
#     #                          handlers=[on_service_state_change])
#     #
#     # try:
#     #     sleep(5)
#     #     zeroconf.close()
#     # except KeyboardInterrupt:
#     #     pass
#     # finally:
#     #     zeroconf.close()
