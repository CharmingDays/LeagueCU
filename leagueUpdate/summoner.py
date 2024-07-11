import typing
from lcu_driver import Connector
from lcu_driver.connection import Connection
from lcu_driver.events.responses import WebsocketEventResponse as Response



class LcuSummoner(object):
    def __init__(self) -> None:
        self.session:Connection

    def updater(self,func):
        async def wrapper(*args,**kwargs):
            self.session = args[0]
            return await func(*args,**kwargs)
        return wrapper
    

    async def summoner_info(self):
        summoner = await self.session.request('get','/lol-summoner/v1/current-summoner')
        return await summoner.json()
            

    async def change_icon(self,icon_id:int):
        pass