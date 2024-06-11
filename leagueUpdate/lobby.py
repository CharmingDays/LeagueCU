import asyncio
import typing
from lcu_driver import Connector
from lcu_driver.connection import Connection
from lcu_driver.events.responses import WebsocketEventResponse as Response




class LcuLobby(object):
    def __init__(self) -> None:
        self.session:Connection
        self.event_data:Response

    def updater(self,func):
        async def wrapper(*args,**kwargs):
            self.session = args[0]
            try:
                self.event_data = args[1]
            except IndexError:
                pass

            await func(*args,**kwargs)
        return wrapper
    
    async def open_lobby(self,lobby_type:str):
        uri ='/lol-lobby/v2/lobby'
    

    async def close_lobby(self):
        uri = '/lol-lobby/v2/lobby'
        await self.session.request('delete',uri)
        

    async def invite_players(self,players:typing.List[str]):
        pass