""" Example of browsing for a service (in this case, HTTP) """

import asyncio
import logging
import socket

from aiopvapi.helpers.aiorequest import AioRequest, PvApiResponseStatusError
from aiopvapi.hub import Hub
from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange

from pv_prompt.print_output import warn

LOGGER = logging.getLogger(__name__)


class Zero:
    def __init__(self, loop):
        self.hubs = []
        self._zeroconf = Zeroconf()
        self.browser = None
        self._loop = loop
        self._tasks = []

    async def add_update_task(self, hub):
        try:
            await hub.query_user_data()
        except PvApiResponseStatusError as err:
            warn("hub {} {} does not respond.".format(hub.name, hub.ip))
            self.hubs.remove(hub)
        finally:
            await hub.request.websession.close()

    async def discover(self, wait_for=5):
        LOGGER.debug("starting discovery")
        self.browser = ServiceBrowser(
            self._zeroconf,
            "_powerview._tcp.local.",
            handlers=[self.on_service_state_change],
        )

        LOGGER.debug("waiting for {} seconds".format(wait_for))
        await asyncio.sleep(wait_for)

        LOGGER.debug("closing discovery")
        self._zeroconf.close()

        LOGGER.debug("waiting for all tasks to finish.")
        try:
            await asyncio.gather(*self._tasks)
        except PvApiResponseStatusError as err:
            LOGGER.error(err)

    def on_service_state_change(
        self, zeroconf, service_type, name, state_change
    ):
        LOGGER.debug(
            "Service %s of type %s state changed: %s"
            % (name, service_type, state_change)
        )

        if state_change is ServiceStateChange.Added:
            info = zeroconf.get_service_info(service_type, name)
            if info:
                address = socket.inet_ntoa(info.address)
                LOGGER.debug("hub found with ip: {}".format(address))
                request = AioRequest(hub_ip=address, loop=self._loop)
                hub = Hub(request)
                self.hubs.append(hub)
                self._tasks.append(
                    self._loop.create_task(self.add_update_task(hub))
                )
