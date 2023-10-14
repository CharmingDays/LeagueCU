from aiohttp import ClientSession

class SocketClient(object):
    def __init__(self) -> None:
        self.session = ClientSession()

    def start(self):
        self.session.ws_connect()
