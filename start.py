import asyncio
import argparse
import aiohttp

from pv_prompt.start import PowerViewPrompt

parser = argparse.ArgumentParser()
parser.add_argument('hub_ip')

if __name__ == "__main__":
    args = parser.parse_args()

    #hub_ip = '192.168.0.118'
    hub_ip = args.hub_ip # '192.168.2.4'
    #hub_ip = '192.168.0.106'
    print("hub ip: {}".format(hub_ip))
    loop = asyncio.get_event_loop()
    session = aiohttp.ClientSession(loop=loop)
    pv = PowerViewPrompt(hub_ip, loop, session)

    loop.run_until_complete(pv.my_coroutine())
    session.close()
