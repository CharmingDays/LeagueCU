import asyncio
from lcu_driver.connection import Connection
from lcu_driver.events.responses import WebsocketEventResponse as Response
from lcu_settings import LcuSettings
import utils



class GameFlowPhase(object):
    def __init__(self) -> None:
        self.session:Connection
        self.settings:LcuSettings
        self.async_event = asyncio.Event()
        self.session_data = {
            'auto_start':True,
            'previous_state':""
        }



    def updater(self,lcu_settings=None):
        def decorator(func):
            async def update_wrapper(*args,**kwargs):
                self.session = args[0]
                try:
                    self.event_data = args[1].data
                except IndexError:
                    pass
                if lcu_settings:
                    if hasattr(self,'settings'):
                        self.settings = lcu_settings
                    else:
                        setattr(self,'settings',lcu_settings)
                return await func(*args,**kwargs)
            return update_wrapper
        return decorator


    async def match_gameflow(self,flow:str):
        
        if self.session_data['previous_state'] == "Matchmaking":
            self.session_data['auto_start'] = False
        
        if flow != "Matchmaking":
            self.session_data['auto_start'] = True
            self.async_event.clear()

        if flow == "Lobby" and self.session_data['auto_start']:
            await self.auto_start_lobby()

        elif flow == 'Matchmaking':
            await self.honoring_player()
        
        elif flow == 'PreEndOfGame':
            await self.honor_teammate()

        elif flow == 'EndOfGame':
            await self.return_to_lobby()

        self.session_data['previous_state'] = flow

    async def clear_async_event(self):
        self.async_event.clear()

    
    async def should_start_queue(self):
        if await self.settings['lobby','auto_start'] and self.session_data['auto_start'] and self.session_data['previous_state'] != "Matchmaking":
            self.async_event.set()
            return True
        return False


    async def auto_start_lobby(self):
        auto_start = await self.settings['lobby','auto_start']
        if auto_start and await self.should_start_queue():
            await self.session.request("post",'/lol-lobby/v2/lobby/matchmaking/search')


    async def honoring_player(self):
        response = await self.session.request("get",'/lol-lobby/v2/lobby')
        lobby_data = await response.json()
        local_player_id = lobby_data['localMember']['summonerId']
        if len(lobby_data['members']) > 1:
            teammate = lobby_data['members'][0]['summonerId'] if lobby_data['members'][0]['summonerId'] != local_player_id else lobby_data['members'][1]['summonerId']
            await self.settings.set(('lobby','honor_player'),teammate)
        else:
            await self.settings.set(('lobby','honor_player'),"")

    
    async def honor_teammate(self):
        skip_delay = self.settings.get(('post_game','skip_honor_delay'))
        if not await self.settings['post_game','honor_teammate'] or await self.settings['lobby','teammate'] == None:
            if skip_delay > 0:
                await asyncio.sleep(skip_delay)
            await self.session.request('post','/lol-honor-v2/v1/honor-player',data={'honorPlayerRequest':False})

        else:
            honor_data = {
                "honorCategory": self.settings.get(('post_game','honor_types','heart')),
                "summonerId": await self.settings['lobby','teammate'],
                "honorPlayerRequest": True
                }
            await asyncio.sleep(6)
            print("Honoring:",honor_data)
            await self.session.request('post','/lol-honor-v2/v1/honor-player',data=honor_data)



    async def return_to_lobby(self):
        if await self.settings['post_game','play_again']:
            if await self.settings['post_game','play_again_delay'] > 0:
                await asyncio.sleep(await self.settings['post_game','play_again_delay'])
            await self.session.request("post",'/lol-lobby/v2/play-again')


    async def champion_select(self):
        pass