import asyncio
import json
import os
from lcu_driver.connection import Connection as socketConnection
from lcu_driver.events.responses import WebsocketEventResponse as socketResponse
import typing
import requests
import yaml
from lcu_settings import LcuSettings
from utils import include_constructor
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


yaml.add_constructor('!include',include_constructor,yaml.FullLoader)



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
        version = requests.get('https://ddragon.leagueoflegends.com/api/versions.json').json()[0]
        response = requests.get(f'https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json')
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
    def is_ban_phase(self) -> bool:
        return self.event_data['actions'][0][0]['inProgress']
    


    @property
    def assigned_role(self) -> str:
        return self.player_data['assignedPosition']



    async def wait_until(self,time_left:float,delay:int) -> None:
        """
        Waits until delay time is met
        """
        while (time_left -1000) > delay and delay > 1:
            await asyncio.sleep(1)
            delay-=1
            time_left-=1000
            



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

    
