import asyncio
import json
import os
from lcu_driver.connection import Connection as socketConnection
from lcu_driver.events.responses import WebsocketEventResponse as socketResponse
import typing
import requests
import yaml
from lcu_settings import LcuSettings
import utils
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


yaml.add_constructor('!include',utils.include_constructor,yaml.FullLoader)



class LcuChampionSelectSession(object):
    def __init__(self) -> None:
        self.event_data:typing.Dict[str,typing.Any] = {}
        self.champion_ids:typing.Dict[str,typing.Any] = {}
        self.session:socketConnection
        self.set_champion_data()
        self.loop:asyncio.AbstractEventLoop = asyncio.get_event_loop()
        self.running_tasks:typing.List = []
        self.settings:LcuSettings


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
        file_name = 'champion_ids.yaml'
        fileDir:str = os.path.dirname(os.path.dirname(__file__))
        try:
            file = open(f"{fileDir}/config/{file_name}")
            self.champion_ids = yaml.load(file,yaml.FullLoader)
            file.close()
        except FileNotFoundError:
            champion_ids = self.fetch_champion_ids()
            self.champion_ids = champion_ids
            with open(f'{fileDir}/config/{file_name}','w') as champion_file:
                yaml.dump(champion_ids,champion_file,Dumper=yaml.Dumper)

 
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
    def banned_champions(self) -> typing.Set[int]:
        """Returns a list of champion IDs that have been banned.

        Returns:
            list: A list of champion IDs that have been banned.
        """
        ban_actions = self.event_data['actions'][0]
        return set([action['championId'] for action in ban_actions if action['completed']])
    

    @property
    def picked_champions(self) -> typing.Set[int]:
        """
        Returns a list of champion IDs for the champions that have been picked.
        
        Returns:
            list: A list of champion IDs.
        """
        pick_actions = self.event_data['actions'][2:]
        return set([pick['championId'] for action in pick_actions for pick in action if pick['completed']])

    @property
    def hovered_champions(self) -> typing.Set[int]:
        """Hovered champions in the current session.

        Returns:
            typing.List: The list of champions hovered by team
        """
        champions = [data['championPickIntent'] for data in self.event_data['myTeam'] if data['championPickIntent'] != 0]
        return set(champions)

    @property
    def is_ban_phase(self) -> bool:
        #NOTE: Use ban reveals instead for check
        return self.event_data['actions'][0][0]['inProgress']
    

    def should_ban(self,champion_id) -> bool:
        return champion_id not in self.hovered_champions and champion_id not in self.banned_champions

    @property
    def assigned_role(self) -> str:
        return self.player_data['assignedPosition']

    @property
    def swap_order(self) -> typing.List[dict]:
        """Swap order for the team
        [
        {
            "cellId": 1,
            "id": 8,
            "state": "AVAILABLE"
        },
        ...
        ]


        Returns:
            typing.List[dict]: The swap order for the team
        """
        return self.event_data['pickOrderSwaps']


    # async def wait_until(self,time_left:float,delay:int) -> None:
    #     """
    #     Waits until delay time is met
    #     """
    #     while (time_left -1000) > delay and delay > 1:
    #         await asyncio.sleep(1)
    #         delay-=1
    #         time_left-=1000
            


    async def disabled_champions(self) -> typing.Set[int]:
        """
        champions that are disabled in the current session
        """
        try:
            uri = '/lol-champ-select/v1/disabled-champions'
            response = await self.session.request('GET',uri)
            data = await response.json()
            return set(data['championIds'])
        except Exception as e:
            return []


    async def not_pickable(self,include_disabled=False) -> typing.Set[int]:
        """
        banned champions + picked champions + disabled champions + (unowned champions?)
        """
        invalid_champions = set()
        if include_disabled:
            disabled_champions:typing.List = await self.disabled_champions()
            invalid_champions.update(disabled_champions)
        
        invalid_champions.update(self.banned_champions)
        invalid_champions.update(self.picked_champions)
        return invalid_champions
    

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


    async def pick_champion_iter(self,champion_list:typing.List[int]):
        # FIXME debug required
        """
        Creates generator of champions pickable in the current session.

        Args:
            champion_list (typing.List): List of champions to pick.

        Yields:
            int: Champion ID to pick.
        """
        not_pickable:typing.Set = await self.not_pickable()
        for champion in champion_list:
            champion_id = self.champion_ids[champion]
            if champion_id not in not_pickable:
                yield champion_id


    
    async def auto_ban(self):
        """Automates the ban phase of the champion select.

        Args:
            ban_dict (typing.Dict[str,typing.List[str]]): Dict of champions to ban given the assigned role.

        """
        action = self.action_data()
        if not action:return
        if self.event_phase == "BAN_PICK" and action['type'] == 'ban':
            ban_delay = self.settings.get(('champion_select','ban_delay'))
            if ban_delay > 0:
                remaining_time = self.event_data['timer']['adjustedTimeLeftInPhase']
                await utils.wait_until(remaining_time,ban_delay)
            champion_pool = self.settings.get(('champion_select',self.assigned_role,'bans'))
            ban_iter = self.ban_champion_iter(champion_pool)
            banning_champion = await ban_iter.__anext__()
            await self.select_champion(banning_champion)
            await self.complete_selection()
    
    async def auto_declare_champion(self):
        """
        Automates the declaration of champion intent in the champion select.
        """
        action = self.action_data()
        if action is None:return
        if self.event_phase == "PLANNING" and self.player_data['championPickIntent'] == 0:
            declare_delay = await self.settings['champion_select','declare_delay']
            if declare_delay > 0:
                phase_time = self.event_data['timer']['adjustedTimeLeftInPhase']
                await utils.wait_until(phase_time,declare_delay)

            champions = await self.settings['champion_select',self.assigned_role,'picks']
            pick_iter = self.pick_champion_iter(champions)
            await self.declare_champion_intent(await pick_iter.__anext__())
    

    async def auto_pick_champion(self):
        """
        Automates the picking phase of the champion select.
        """
        action_data = self.action_data()
        if action_data is None:return
        if self.event_phase == "BAN_PICK" and action_data['type'] == 'pick':
            champion_pool = await self.settings['champion_select',self.assigned_role,'picks']
            pick_iter = self.pick_champion_iter(champion_pool)
            picking_champion:int = await pick_iter.__anext__()
            if self.event_phase == "BAN_PICK" and action_data['type'] == 'pick' and self.player_data['championPickIntent'] == 0:
                #Champion not selected
                await self.select_champion(picking_champion)

            pick_delay = await self.settings['champion_select','pick_delay']
            if pick_delay > 0:
                time_remaining = self.event_data['timer']['adjustedTimeLeftInPhase']
                await utils.wait_until(time_remaining,pick_delay)
            await self.complete_selection()





    async def ban_and_pick(self):
        await self.auto_declare_champion()
        await self.auto_ban()
        await self.auto_pick_champion()

    async def trade_position(self,player_position:str) -> None:
        """Swap pick order with another player.

        Args:
            player_position (int): The position to pick
        """
        #NOTE only supports first and last ATM
        #NOTE full support for all positions will be added later
        # player_position = 3 if player_position > 3 else player_position
        available_trades_uri  = self.event_data['pickOrderSwaps']
        uri = ""
        if player_position not in ['first','last']:
            player_position = 'last'
        if player_position == 'first':
            uri+= f"/lol-champ-select/v1/session/trades/{available_trades_uri[0]['id']}/request"
        else:
            uri+= f"/lol-champ-select/v1/session/trades/{available_trades_uri[-1]['id']}/request"
        await self.session.request('POST',uri)


