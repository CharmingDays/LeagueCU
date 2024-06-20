import asyncio
import json
import os
from lcu_driver.connection import Connection as socketConnection
from lcu_driver.events.responses import WebsocketEventResponse as socketResponse
import typing
import requests
from collections import deque

RED_COLOR = "\033[31m"
GREEN_COLOR = "\033[32m"
RESET_COLOR = "\033[0m"
BLUE_COLOR = "\033[34m"
"""
actions: List
    [
    [0] -- > ban
    [1] -- > ban reveals
    [2] -- > pick (1st pick)
    [3] -- > pick (2 pick)
    [4] -- > pick (2 pick)
    [5] -- > pick (2 pick)
    [6] -- > pick (2 pick)
    [7] -- > pick (last pick)
    ]
"""



def verify_action(func):
    """Decorator function to verify if the user can perform an action by checking actions array.

    Args:
        func (func): The function to be decorated.
    """
    async def do_nothing():
        return None
    def action_wrapper(self,*args, **kwargs):
        action:typing.Dict[str,typing.Any] = self.event_data
        if action is None or action.get('myTeam',None) is None:
            return do_nothing()  # Skip the function invocation
        return func(self,*args, **kwargs)
    return action_wrapper



def trace_methods(cls):
    for name, method in cls.__dict__.items():
        if callable(method):
            setattr(cls, name, trace_method(method))
    return cls

def trace_method(method):
    def wrapper(*args, **kwargs):
        print(f'{BLUE_COLOR}{method.__name__}{RESET_COLOR}')
        return method(*args, **kwargs)
    return wrapper




class LcuChampionSelectSession(object):
    def __init__(self) -> None:
        self.event_data:typing.Dict[str,typing.Any] = {}
        self.champion_ids:typing.Dict[str,typing.Any] = {}
        self.session:socketConnection
        self.set_champion_data()
        self.loop:asyncio.AbstractEventLoop = asyncio.get_event_loop()
        self.running_tasks:typing.Dict = {}



    def fetch_champion_ids(self):
        response = requests.get('https://ddragon.leagueoflegends.com/cdn/11.16.1/data/en_US/champion.json')
        if response.status_code != 200:
            backupURL = 'https://gist.githubusercontent.com/CharmingDays/6e7d673403439b697b10a2d6100e2288/raw/e7b9528ca76e5cf62d32622cfb11d88cddcd7322/champid.json'
            response = requests.get(backupURL)
            if response.status_code != 200:
                raise requests.exceptions.RequestException("Could not get champion data")
        champions:dict = {}
        for name,values in response.json()['data'].items():
            championId= int(values['key'])
            champions[name.lower()] = championId
            champions[championId] = championId
        return champions
    

    def set_champion_data(self):
        fileDir:str = os.path.dirname(os.path.dirname(__file__))
        try:
            file = open(f"{fileDir}/'championIds.json")
            data = json.load(file)
            self.champion_ids = data
            file.close()
        except FileNotFoundError:
            champion_ids = self.fetch_champion_ids()
            self.champion_ids = champion_ids
            with open('championIds.json','w') as champion_file:
                json.dump(champion_ids,champion_file)

    def updater(self, func):
        """
        Decorator function for updating session data.

        Args:
            func (function): The function to be decorated.

        Returns:
            function: The decorated function.

        Raises:
            TypeError: If the required arguments 'session' and 'data' are not provided.

        """
        async def update_wrapper(*args,**kwargs):
            self.session = args[0]
            self.event_data = args[1].data
            return await func(*args,**kwargs)
        return update_wrapper

    @property
    def event_phase(self):
        return self.event_data['timer']['phase']


    @property
    def cell_id(self):
        return self.event_data['localPlayerCellId']

    @property
    def player_data(self) -> typing.Dict[str, typing.Any]:
        """Returns player data from myTeam array in event data.

        Returns:
            typing.Dict[str, typing.Any]: The player data.
        """
        # return next((data for data in self.event_data['myTeam'] if data['cellId'] == cell_id), None)
        cell_id = self.cell_id
        teamData = self.event_data['myTeam']
        for player in teamData:
            if player['cellId'] == cell_id:
                return player
        return None

    @property
    def banned_champions(self):
        """Returns a list of champion IDs that have been banned.

        Returns:
            list: A list of champion IDs that have been banned.
        """
        ban_actions = self.event_data['actions'][0]
        return [action['championId'] for action in ban_actions if action['completed']]
    

    @property
    def picked_champions(self):
        """
        Returns a list of champion IDs for the champions that have been picked.
        
        Returns:
            list: A list of champion IDs.
        """
        pick_actions = self.event_data['actions'][2:]
        return [pick['championId'] for action in pick_actions for pick in action if pick['completed']]

    @property
    def hovered_champions(self) -> typing.List[int]:
        """Hovered champions in the current session.

        Returns:
            typing.List: The list of champions hovered by team
        """
        champions = [data['championPickIntent'] for data in self.event_data['myTeam'] if data['championPickIntent'] != 0]
        return champions

    @property
    def is_ban_phase(self) -> bool:
        return self.event_data['actions'][0][0]['inProgress']
    

    def should_ban(self,champion_id) -> bool:
        return champion_id not in self.hovered_champions and champion_id not in self.banned_champions

    @property
    def assigned_role(self) -> str:
        return self.player_data['assignedPosition']


    async def wait_until(self,total_time,adjust_time,delay:int) -> None:
        """
        Waits until delay time is met
        """
        while total_time- adjust_time < delay:
            await asyncio.sleep(1)
            adjust_time-=1000

    async def disabled_champions(self) -> typing.Dict[str,typing.Any]:
        """
        champions that are disabled in the current session
        """
        try:
            uri = '/lol-champ-select/v1/disabled-champions'
            response = await self.session.request('GET',uri)
            data = await response.json()
            return data['championIds']
        except Exception as e:
            return []


    async def not_pickable(self) -> typing.List[int]:
        """
        banned champions + picked champions + disabled champions + (unowned champions?)
        """
        champions:typing.List = await self.disabled_champions()
        champions.extend(self.banned_champions)
        champions.extend(self.picked_champions)
        return champions
    

    def get_action_data(self, action_type: str) -> typing.Dict[str, typing.Any] | None:
        """Get data of specific action from actions array

        Args:
            action_type (str): The incomplete action type to retrieve

        Returns:
            typing.Dict: The data of the action.
        """
        # action = next((action for action_list in self.event_data['actions'] if action_list[0]['type'] == action_type.lower() for action in action_list if action['actorCellId'] == cell_id and not action['completed']), None)
        cell_id = self.cell_id
        all_actions = self.event_data['actions']
        for action_list in all_actions:
            for action in action_list:
                if action['actorCellId'] == cell_id and not action['completed'] and action['type'] == action_type.lower():
                    return action
        return None



    def action_data(self) -> typing.Dict[str,typing.Any] | None:
        """Gets the current action data in progress.

        Returns:
            typing.Dict[str,typing.Any] | None: The action data or None if no action is in progress.
        """
        cell_id = self.cell_id
        all_actions = self.event_data['actions']
        for action_list in all_actions:
            for action in action_list:
                if action['actorCellId'] == cell_id and action['isInProgress']:
                    return action
        return None

    

    async def declare_champion_intent(self,champion_id:int|str) -> None:
        """
        Primarily used for declaring champion pick intent, but can be used to select champion for pick and ban (ban is not recommended for this method)

        Args:
            champion_id (int | str): The ID of the champion

        Raises:
            ValueError: Champion not found
        """
        if champion_id not in self.champion_ids:
            raise ValueError(f"Champion with id {champion_id} does not exist.")
        
        action = self.get_action_data('pick')
        if not action:return
        if action is not None:
            action: dict = action
            action['championId'] = self.champion_ids[champion_id]
            uri = f'/lol-champ-select/v1/session/actions/{action["id"]}'
            await asyncio.wait_for(self.session.request('PATCH',uri,data=action), timeout=5)

    
    
    async def select_champion(self,champion_id:int|str) -> None:
        """Selects the champion at current given phase action. (Mostly for banning champions & picking)

        Args:
            champion_id (int | str): The champion identifier.

        """

        action = self.action_data()
        if not action:return
        action['championId'] = self.champion_ids[champion_id]
        uri = f'/lol-champ-select/v1/session/actions/{action["id"]}'
        await asyncio.wait_for(self.session.request('PATCH',uri,data=action), timeout=5)



    async def complete_selection(self) -> None:
        """
        Complete the selection action.
        """
        # Suggestion 2: Add type hints for the action variable.
        action: dict = self.action_data()
        if not action:return
        uri = f'/lol-champ-select/v1/session/actions/{action["id"]}/complete'
        # Suggestion 1: Add a timeout to the POST request to avoid hanging indefinitely.
        await asyncio.wait_for(self.session.request('POST', uri, data=action), timeout=5)



    async def ban_champion_iter(self,champion_list):
        """Creates generator of champions bannable in the current session.

        Args:
            champion_list (typing.List): List of champions to ban.

        Yields:
            int: Champion ID to ban.
        """
        for champion in champion_list:
            champion_id = self.champion_ids[champion]
            if self.should_ban(champion_id):
                yield champion_id


    async def pick_champion_iter(self,champion_list):
        """
        Creates generator of champions pickable in the current session.

        Args:
            champion_list (typing.List): List of champions to pick.

        Yields:
            int: Champion ID to pick.
        """
        not_pickable = set(await self.not_pickable())
        for champion in champion_list:
            champion_id = self.champion_ids[champion]
            if champion_id not in not_pickable:
                yield champion_id

    

    
    async def auto_ban(self,ban_dict:typing.Dict[str,typing.List[str]],delay=0):
        """Automates the ban phase of the champion select.

        Args:
            ban_dict (typing.Dict[str,typing.List[str]]): Dict of champions to ban given the assigned role.

        """
        action = self.action_data()
        if not action:return
        if self.event_phase == "BAN_PICK" and action['type'] == 'ban':
            if delay > 30:
                delay = 30
            delay*=1000
            ban_iter = self.ban_champion_iter(ban_dict[self.assigned_role]['bans'])
            banning_champion = await ban_iter.__anext__()
            remaining_time = (self.event_data['timer']['adjustedTimeLeftInPhase']/1000)
            total_time = self.event_data['timer']['totalTimeInPhase']
            await self.wait_until(total_time,remaining_time,delay)
            await self.select_champion(banning_champion)
            await self.complete_selection()
    

    
    async def confirm_champion_intent(self,champion:int,delay:int):
        delay*=1000
        while self.event_phase == "PLANNING" and self.player_data['championPickIntent'] == 0:
            adjusted_time = self.event_data['timer']['adjustedTimeLeftInPhase']
            total_time = self.event_data['timer']['totalTimeInPhase']
            await self.wait_until(total_time,adjusted_time,delay)
            await self.declare_champion_intent(champion)


    async def auto_pick(self,pick_dict:typing.Dict[str,typing.List[str]],delay:int=0):
        """Automates the pick phase of the champion select.

        Args:
            pick_dict (typing.Dict[str,typing.List[str]]): Dict of champions to pick given the assigned role.


        """
        action = self.action_data()
        if action is None:return
        pick_iter = self.pick_champion_iter(pick_dict[self.assigned_role]['picks'])
        picking_champion:int = await pick_iter.__anext__()
        if self.event_phase == "PLANNING" and self.player_data['championPickIntent'] == 0:
            return await self.declare_champion_intent(picking_champion)

        confirm_pick_intent = self.loop.create_task(self.confirm_champion_intent(picking_champion,delay))
        await confirm_pick_intent


        if self.event_phase == "BAN_PICK" and action['type'] == 'pick' and self.player_data['championPickIntent'] == 0:
            #Champion banned or picked by another player
            await self.select_champion(picking_champion)

        time_remaining = self.event_data['timer']['adjustedTimeLeftInPhase']
        total_time = self.event_data['timer']['totalTimeInPhase']
        await self.wait_until(total_time,time_remaining,delay)
        await self.complete_selection()        

    async def trade_position(self,player_position:int) -> None:
        available_trades_uri  = "/lol-champ-select/v1/session/trades"
        response = await self.session.request('GET',available_trades_uri)
        trade_options = await response.json()
        uri = f"/lol-champ-select/v1/session/trades/{id}/request"


    async def auto_runes(self):
        pass

    async def auto_summoner_spells(self):
        pass





class UnitTest(LcuChampionSelectSession):
    def __init__(self) -> None:
        super().__init__()
        self.loaded_files = []
        self.files = self.generate_files()
    

    def generate_files(self) -> typing.Generator:
        path = r'D:\Developer\LeagueCU\testData'
        files:typing.List = os.listdir(path)
        for file in files:
            yield os.path.join(path, file)


    def load_file(self):
        path = next(self.files)
        try:
            file = open(path,'r',encoding='utf-8')
            self.event_data = json.loads(file.read())
        except FileNotFoundError:
            raise FileNotFoundError(f"File {path} not found.")
        finally:
            file.close()

