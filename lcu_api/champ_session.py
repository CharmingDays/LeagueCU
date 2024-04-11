import json
import os
import aiohttp
from lcu_driver.connection import Connection as socketConnection
from lcu_driver.events.responses import WebsocketEventResponse as socketResponse
import typing
import requests
from collections import deque




class ChampionSession(object):
    """Class for handling champion select session data"""
    def __init__(self) -> None:
        self.data:typing.Dict
        self.champData:typing.Dict[str,str] = self.get_champions()
        self.session:socketConnection


    def get_champions(self) -> typing.Dict[str, str]:
        """Get the dictionary of champion names and their corresponding IDs.

        This method retrieves the champion data from the League of Legends Data Dragon API
        and returns a dictionary containing the champion names as keys and their IDs as values.

        If the 'champIds.json' file is not found in the current directory, the method
        fetches the latest champion data from the API, saves it to the file, and returns
        the dictionary. Otherwise, it reads the data from the file and returns the dictionary.

        Returns:
            typing.Dict[str, str]: A dictionary containing the champion names as keys and
            their IDs as values.
        """
        fileDir = os.path.dirname(__file__)
        if "champIds.json" not in os.listdir(fileDir):
            # TODO: include version check of champion ids
            dragonUrl = 'https://ddragon.leagueoflegends.com/api/versions.json'
            version = requests.get(dragonUrl).json()[0]
            url = f'https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json'
            champions: typing.Dict = {}
            rawChamps = requests.get(url).json()
            for name, values in rawChamps['data'].items():
                champions[name.lower()] = int(values['key'])

            with open(f"{fileDir}/championIds.json", 'w') as file:
                file.write(json.dumps(champions))
            return champions
        with open(f"{fileDir}/championIds.json", 'r') as champs:
            return json.loads(champs)
    

    def update_data(self,connection:socketConnection,event:socketResponse)->bool:
        """Updates the session data
        Args:
            data (socketResponse): The websocket response data
        """
        self.session = connection
        self.data = event.data
            
        
    @property
    def session_phase(self) ->str:
        if self.data:
            return self.data['timer']['phase']


    @property
    def localPlayerCellId(self):
        return self.data['localPlayerCellId']


    @property
    def playerData(self) ->typing.Dict:
        for playerData in self.data['myTeam']:
            if playerData['cellId'] == self.localPlayerCellId:
                return playerData


    @property
    def banned_champs(self):
        bannedChamps = []
        for actions in self.data['actions']:
            for action in actions:
                if action['completed'] and action['type'] == 'ban':
                    bannedChamps.append(action['championId'])

        return bannedChamps
    

    def not_pickable(self) -> typing.List:
        """Returns list of champions that are not pickable

        Returns:
            typing.List: The list of champions that aren't pickable
        """
        champs = []
        for user in self.data['myTeam']: 
            #my team
            # print(user)
            if user['championId'] not in champs:
                champs.append(user['championId'])
        
        for user in self.data['theirTeam']: 
            #enemy team
            if user['championId'] not in champs:
                champs.append(user['championId'])
        
        champs.extend(self.banned_champs)
        return champs



    def is_player_turn(self) -> typing.Union[bool,typing.Dict]:
        """Returns the player's action data dict if true

        Returns:
            typing.Union[bool,typing.Dict]: The player action data
        """
        for actionType in self.data['actions']:
            for action in actionType:
                if action['actorCellId'] == self.localPlayerCellId and not action['completed'] and action['isInProgress']:
                    return action
                
        return False
                
    
    def champ_identity(self,champ:str|int) -> str|int:
        """Return the opposite identity of the champion

        Args:
            identifier (str | int): The champion identity

        Returns:
            typing.Generator: Generator of champion ids
        """
        if isinstance(champ,int):
            champs = {value:key for key,value in self.champData.items()}
            if champ in champs:
                return champ
            return 0
        if isinstance(champ,str):
            return self.champData.get(champ,0)

    async def declare_champion(self,champ:str|int):
        champId = self.champ_identity(champ)
        declareData = None
        for actionType in self.data['actions']:
            for action in actionType:
                if action['actorCellId'] == self.localPlayerCellId and not action['completed'] and action['type'] == "pick":
                    declareData=action
                    break

        if not declareData:
            return
        
        declareData['championId'] = champId
        uri = f'/lol-champ-select/v1/session/actions/{declareData["id"]}'
        await self.session.request('PATCH',uri,data=declareData)
        


    async def select_champ(self,champ:str|int):
        """Selects the champion

        Args:
            champ (str | int): _description_
        """
        champId = self.champ_identity(champ)
        actionData = self.is_player_turn()
        if not actionData:
            return 
        
        uri = f'/lol-champ-select/v1/session/actions/{actionData["id"]}'
        actionData['championId'] = champId
        await self.session.request("PATCH",uri,data=actionData)


    async def lock_champ_in(self,champ:str|int) -> aiohttp.ClientResponse:
        """
        Automates the declare,hover, and lock in process
        Args:
            champ (str | int): The champion to select given ID

        Returns:
            aiohttp.ClientResponse: http response of the request
        """
        champId = self.champ_identity(champ)
        actionData = self.is_player_turn()
        if not actionData:
            return
        if self.playerData['championPickIntent'] ==0 and len(self.banned_champs) <10:
            await self.declare_champion(champId)

        if len(self.banned_champs) >=10 and champId not in self.not_pickable():
            await self.post_champ()

    def hovered_champions(self):
        return [champ['championPickIntent'] for champ in self.data['myTeam']]


    def should_ban(self,champId):
        # TODO add disabled champions, already banned champions
        champList = self.hovered_champions()
        return champId not in champList
    

    async def auto_ban(self, champList: typing.List[str|int]):
        """
        Automatically selects and bans a champion from the given list.

        Args:
            champList (List[str|int]): A list of champion names or IDs.

        Returns:
            None
        """
        champId = deque([self.champ_identity(champ) for champ in champList])
        actionData = self.is_player_turn()
        if not actionData:
            return
        if self.session_phase == "BAN_PICK" and actionData['type'] == 'ban':
            try:
                while not self.should_ban(champId[0]):
                    champId.popleft()
            except IndexError:
                return
            await self.select_champ(champId[0])
            await self.post_champ()




# GAME_STARTING
    async def auto_pick(self,laneChamps:typing.Dict[str,typing.List[str]]) -> aiohttp.ClientResponse:
        actionData = self.is_player_turn()
        champIds = deque([self.champ_identity(champ) for champ in laneChamps[self.playerData['assignedPosition']]])
        if self.playerData['championPickIntent'] == 0 and self.session_phase == "PLANNING":
            await self.declare_champion(champIds[0])
        
        if not actionData:
            return
        
        elif actionData['type'] == 'pick' and self.session_phase == 'BAN_PICK':
            not_pickable_champs = self.not_pickable()
            try:
                while champIds[0] in not_pickable_champs:
                    champIds.popleft()
            except IndexError:
                return #all champions picked
            if self.playerData['championPickIntent'] == 0 or self.playerData['championId'] == 0:
                await self.select_champ(champIds[0])
            elif self.playerData['championPickIntent'] != 0 and self.playerData['championPickIntent'] != champIds[0]:
                await self.select_champ(self.playerData['championPickIntent'])
            uri = f"/lol-champ-select/v1/session/actions/{actionData['id']}/complete"
            await self.session.request('POST',uri,data=actionData)


    async def post_champ(self) -> aiohttp.ClientResponse:
        """Lock-in/Ban the currently hovered/selected champion

        Returns:
            aiohttp.ClientResponse: The http response
        """
        actionData = self.is_player_turn()
        actionData
        if actionData and actionData['championId'] != 0:
            uri = f"/lol-champ-select/v1/session/actions/{actionData['id']}/complete"
            response = await self.session.request('POST',uri,data=actionData)
            return response

