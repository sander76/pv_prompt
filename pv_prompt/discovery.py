import logging

import asyncdns
from nmb.NetBIOS import NetBIOS
from prompt_toolkit.completion import WordCompleter

from pv_prompt.base_prompts import BasePrompt, Command
from pv_prompt.print_output import print_waiting_done, info, print_table, warn

LOGGER = logging.getLogger(__name__)

NETBIOS_HUB2_NAME = "PowerView-Hub"
NETBIOS_HUB1_NAME = "hub"


class Discovery(BasePrompt):
    def __init__(self):
        super().__init__()
        self._prompt = "Hub connection: "
        self.register_commands(
            {
                "d": Command(function_=self._discover),
                "c": Command(function_=self.connect, autoreturn=True),
            }
        )
        self._ip_suggestions = None
        self._ip_completer = None

    async def _discover(self, *args, **kwargs):
        self._ip_suggestions = []

        resolver = asyncdns.MulticastResolver()

        query = asyncdns.Query("_powerview._tcp.local.", asyncdns.ANY, asyncdns.IN)
        done = print_waiting_done("Discovering hubs")

        r = await resolver.lookup(query)
        # r = f.result()

        await done()

        for _res in r.answers:
            if _res.rr_type == asyncdns.A:
                add = str(_res.address)
                info(add)
                self._ip_suggestions.append(add)
        self._populate_completer()
        #
        # zero = Zero(self.loop)
        # done = print_waiting_done("Discovering hubs")
        # LOGGER.debug("discover command fire")
        # await zero.discover()
        # LOGGER.debug("discovery done")
        # await done()
        # if zero.hubs:
        #     self.print_hub_table()
        #     for _hub in zero.hubs:
        #         print_key_values(_hub.name, _hub.ip)
        #         self._ip_suggestions.append(_hub.ip)
        # self._populate_completer()

    async def _discover_hub1(self, *args, **kwargs):
        nb = NetBIOS()
        info("Discovering hubs...")
        LOGGER.debug("discover command fire")
        self._ip_suggestions = nb.queryName(NETBIOS_HUB1_NAME, timeout=5)
        if self._ip_suggestions:
            self.print_hub_table()
            for _hub in self._ip_suggestions:
                print_table("hub1", _hub)
            self._populate_completer()
        else:
            warn("...Discovery timed out")

    def print_hub_table(self):
        print("")
        print_table("NAME", "IP ADDRESS")
        print_table("----", "----------")

    def _populate_completer(self):
        self._ip_completer = WordCompleter(self._ip_suggestions)

    async def connect(self, *args, **kwargs):
        pr = BasePrompt()
        ip = await pr.current_prompt(
            "Enter ip address: ",
            toolbar="Enter a valid ip address: 129.168.2.3",
            autoreturn=True,
            autocomplete=self._ip_completer,
        )
        LOGGER.debug("entered ip is : {}".format(ip))
        try:
            self.validate_ip(ip)
        except ValueError:
            warn("Invalid ip entered.")
        else:
            LOGGER.debug("returning ip address: {}".format(ip))
            return "http://{}".format(ip)

    def validate_ip(self, ip):
        vals = ip.split(".")
        try:
            ints = (int(val) for val in vals)
        except ValueError:
            raise ValueError
        for _int in ints:
            if _int < 0 or _int > 256:
                raise ValueError
