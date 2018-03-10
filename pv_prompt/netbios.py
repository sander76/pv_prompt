# def queryName(self, name, ip='', port=137, timeout=30):
#     """
#     Send a query on the network and hopes that if machine matching the *name* will reply with its IP address.
#
#     :param string ip: If the NBNSProtocol instance was instianted with broadcast=True, then this parameter can be an empty string. We will leave it to the OS to determine an appropriate broadcast address.
#                       If the NBNSProtocol instance was instianted with broadcast=False, then you should provide a target IP to send the query.
#     :param integer port: The NetBIOS-NS port (IANA standard defines this port to be 137). You should not touch this parameter unless you know what you are doing.
#     :param integer/float timeout: Number of seconds to wait for a reply, after which the method will return None
#     :return: A list of IP addresses in dotted notation (aaa.bbb.ccc.ddd). On timeout, returns None.
#     """
#     assert self.sock, 'Socket is already closed'
#
#     trn_id = random.randint(1, 0xFFFF)
#     data = self.prepareNameQuery(trn_id, name)
#     if self.broadcast and not ip:
#         ip = '<broadcast>'
#     elif not ip:
#         self.log.warning(
#             'queryName: ip parameter is empty. OS might not transmit this query to the network')
#
#     self.write(data, ip, port)
#
#     return self._pollForNetBIOSPacket(trn_id, timeout)
#
# def _pollForNetBIOSPacket(self, wait_trn_id, timeout):
#     end_time = time.time() - timeout
#     while True:
#         try:
#             _timeout = time.time() - end_time
#             if _timeout <= 0:
#                 return None
#
#             ready, _, _ = select.select([self.sock.fileno()], [], [], _timeout)
#             if not ready:
#                 return None
#
#             data, _ = self.sock.recvfrom(0xFFFF)
#             if len(data) == 0:
#                 raise NotConnectedError
#
#             trn_id, ret = self.decodePacket(data)
#
#             if trn_id == wait_trn_id:
#                 return ret
#         except select.error as ex:
#             if type(ex) is tuple:
#                 if ex[0] != errno.EINTR and ex[0] != errno.EAGAIN:
#                     raise ex
#             else:
#                 raise ex
#
#
# import asyncio
#
# class EchoClientProtocol:
#     def __init__(self, message, loop):
#         self.message = message
#         self.loop = loop
#         self.transport = None
#
#     def connection_made(self, transport):
#         self.transport = transport
#         print('Send:', self.message)
#         self.transport.sendto(self.message.encode())
#
#     def datagram_received(self, data, addr):
#         print("Received:", data.decode())
#
#         print("Close the socket")
#         self.transport.close()
#
#     def error_received(self, exc):
#         print('Error received:', exc)
#
#     def connection_lost(self, exc):
#         print("Socket closed, stop the event loop")
#         loop = asyncio.get_event_loop()
#         loop.stop()
#
# loop = asyncio.get_event_loop()
# message = "Hello World!"
# connect = loop.create_datagram_endpoint(
#     lambda: EchoClientProtocol(message, loop),
#     remote_addr=('127.0.0.1', 9999))
# transport, protocol = loop.run_until_complete(connect)
# loop.run_forever()
# transport.close()
# loop.close()