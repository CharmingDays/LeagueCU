import asyncio
import typing
from lcu_driver import Connector
from lcu_driver.connection import Connection
from lcu_driver.events.responses import WebsocketEventResponse as Response
from lcu_settings import LcuSettings


class LcuLobby(object):
    def __init__(self) -> None:
        self.session:Connection
        self.event_data:Response
        self.settings:LcuSettings


    def updater(self,var=None):
        def decorator(func):
            async def update_wrapper(*args,**kwargs):
                self.session = args[0]
                try:
                    self.event_data = args[1]
                except IndexError:
                    pass
                if var:
                    if hasattr(self,'settings'):
                        self.settings = var
                    else:
                        setattr(self,'settings',var)
                return await func(*args,**kwargs)
            return update_wrapper
        return decorator
    
    async def lobby_settings(self):
        if hasattr(self,'settings'):
            return await self.settings['lobby']
        return {}
    
    async def open_lobby(self,lobby_type:str):
        # make party open to any friends.
        uri ='/lol-lobby/v2/lobby'
    

    async def close_lobby(self):
        uri = '/lol-lobby/v2/lobby'
        response =await self.session.request('delete',uri)
        if not response.ok:
            return {'errorCode':response.status_code}
        

    async def invite_players(self,players:typing.List[str]):
        pass


    async def lobby_info(self) ->typing.Dict[str,typing.Any]:
        uri = '/lol-lobby/v2/lobby'
        response = await self.session.request('get',uri)
        if not response.ok:
            return {'errorCode':response.status_code}
        return await response.json()   

    async def update_party_members(self):
        party_members = await self.lobby_info()
        if not party_members or party_members.get('errorCode'):
            await self.settings['lobby']['party_members'].clear()
            return
        for member in party_members:
            self.settings['lobby']['party_members'].append(member['summonerId'])
        return
    
    async def find_match(self):
        uri = '/lol-lobby/v2/lobby/matchmaking/search'
        response = await self.session.request('post',uri)
        if not response.ok:
            return {'errorCode':response.status_code}



    async def cancel_queue(self):
        uri = '/lol-lobby/v2/lobby/matchmaking/search'
        response = await self.session.request('delete',uri)
        if not response.ok:
            return {'errorCode':response.status_code}


    async def create_lobby(self,lobby_type:str="RANKED"):
        uri = '/lol-lobby/v2/lobby'
        queue_dict= {
            "DRAFT": 400,
            "RANKED":420,
            "FLEX":440,
            "ARAM":450,
            "BLIND":430,
            "CUSTOM":"CUSTOM_GAME",
            "PRACTICE":"PRACTICETOOL"
        }
        payload={
            "queueId": queue_dict[lobby_type.upper()]
        }
        resp = await self.session.request('post',uri,data=payload)
        if not resp.ok:
            return {'errorCode':resp.status_code}
        return await resp.json()