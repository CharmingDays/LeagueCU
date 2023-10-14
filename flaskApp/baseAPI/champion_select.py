import asyncio
from typing import Union
from lcu_driver.connection import Connection
from lcu_driver.events.responses import WebsocketEventResponse as EventResponse
import json
import aiohttp
class ChampSelect(object):
    """
    Champion select methods for the LCU
    """
    def __init__(self) -> None:
        self.session:Connection = Connection
        self.sessionData:EventResponse = EventResponse
        self.champion_names = {}
        self.champion_ids = {}
        self.patch_version=0


    def __call__(self):
        """
        Init the data for later uses
        """
        asyncio.run(self.__dd_version())
        asyncio.run(self.__get_champion_names())

    def updateData(self,conn:Connection,event:EventResponse):
        self.session= conn
        self.sessionData= event
    
    async def external_get(self,url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                await response.read()
                return response
            

    async def __dd_version(self):
        """
        Retrieves the data dragon version for the Data Dragon API
        """
        url ='https://ddragon.leagueoflegends.com/api/versions.json'
        response = await self.external_get(url)
        versionData = await response.json()
        self.patch_version = versionData[0]
    
    async def __get_champion_names(self):
        url = f'http://ddragon.leagueoflegends.com/cdn/{self.patch_version}/data/en_US/champion.json'
        response = await self.external_get(url)
        data = await response.json()
        if response.ok:
            for name,value in data['data'].items():
                self.champion_names[name] = value['key']
                self.champion_ids[int(value['key'])] = name
            return True
        return False

    @property
    def timers(self):
        #NOTE: INCOMPLETE
        return self.sessionData.data['timer']

    @property
    def selected_champion(self):
        """
        Checks what champion if any current summoner has locked in (already selected)
        0 -> None
        """
        return self.sessionData.data['myTeam'][self.sessionData.data['localPlayerCellId']]


    def hovered_ban(self):
        """
        Return the current hovered ban intent champion ID. 0 if none
        """
        local = self.currentActionData
        return local['championId']

    async def bannable_champions(self):
        """
        Returns a list of bannable champion ids
        """
        uri = "/lol-champ-select/v1/bannable-champion-ids"
        data = await self.session.request('get',uri)
        return await data.json()

    async def pickable_champions(self):
        """
        Get the current pickable champions in session
        """
        uri = "/lol-champ-select/v1/pickable-champion-ids"
        data = await self.session.request('get',uri)
        return await data.json()

    @property
    def local_player_cell_id(self):
        """
        Returns the localPlayerCellId which is used to identify user's actions.
        """
        return self.sessionData.data['localPlayerCellId']


    @property
    def player_position(self,cellId=None):
        """
        Position of local player or of given cellId
        """
        if cellId is None:
            cellId = self.local_player_cell_id
            return self.local_player_team_data['assignedPosition']

        for playerData in self.sessionData.data['myTeam']:
            if playerData['cellId'] == cellId:
                return playerData['assignedPosition']
            
            

    @property
    def local_player_team_data(self):
        """
        Returns team data of local player
        """
        localId = self.local_player_cell_id
        for i in self.sessionData.data['myTeam']:
            if i['cellId'] == localId:
                return i


    def hovered_champions(self):
        """
        Returns a list of champions that team has hovered
        """
        champions= []
        for playerData in self.sessionData.data['myTeam']:
            if playerData['championPickIntent'] !=0:
                champions.append(playerData['championPickIntent'])
        
        return champions

    @property
    def currentActionData(self):
        """
        Returns the current local player's cell data that is in progress
        """
        sessionData = self.sessionData.data
        for action in sessionData['actions']:
            for actionData in action:
                if not actionData['completed'] and actionData['isInProgress'] and actionData['actorCellId'] == sessionData['localPlayerCellId']:
                    return actionData


        return False


    def get_phase_data(self,actorCellId:int,phase:str):
        """
        """
        for data in self.sessionData.data['actions']:
            for actorData in data:
                if actorData['actorCellId'] == actorCellId and actorData['type'] == phase:
                    return actorData

    def actionData(self,actionType:str):
        """
        Returns the local player's data for picking phase, mainly looking for the "id" from actions in pick phase
        """
        #get the summoner's pick id
        actions = self.sessionData.data['actions']
        for action in actions:
            for actionData in action:
                if actionData['type'] == actionType and not actionData['completed'] and actionData['actorCellId'] == self.sessionData.data['localPlayerCellId']:                    
                    return actionData


    @property
    def selected_champion(self):
        """
        returns the currently selected champion
        """
        data = self.actionData()
        return data['championId']

    def champion_by_name(self,champion):
        """
        Returns the id of the champion by name
        """
        championNames = {key.upper(): value for key,value in self.champion_names.items()}
        if champion.upper() not in championNames:
            raise f"Champion {champion} not found"
        return int(championNames[champion.upper()])


    async def hover_champion(self,champion):
        """
        Hover the given champion
        """
        #NOTE: CLICKING ON A CHAMPION MANUALLY WILL TAKE CONTROL OVER AND THIS WILL NOT WORK ANYMORE
        #NOTE: THIS SHOULD BE USED ONLY TO BAN/PICK CHAMPIONS
        #NOTE: for ban/pick phase
        hoverData = self.actionData('pick')
        uri = f'/lol-champ-select/v1/session/actions/{hoverData["id"]}'
        if type(champion) != int:
            champion = self.champion_by_name(champion)
        hoverData['championId'] = champion
        response=await self.session.request('patch',uri,data=hoverData)
        return response


    async def select_champion(self,championId):
        #NOTE: CLICKING ON A CHAMPION MANUALLY WILL TAKE CONTROL OVER AND THIS WILL NOT WORK ANYMORE
        #NOTE: THIS SHOULD BE USED ONLY TO BAN/PICK CHAMPIONS
        """
        Sort of an alias to `hover_champion()`
        """
        if type(championId) != int:
            #convert to int 
            championId = self.champion_by_name(championId)

        if self.is_final_phase:
            #finalization phase already, champions already locked in
            return False
        phaseData =  self.currentActionData #the player pick data
        #change the values to local player's 
        phaseData['championId'] = championId
        selectUri = f'/lol-champ-select/v1/session/actions/{phaseData["id"]}'
        data = await self.session.request('patch',selectUri,data=phaseData) #Hover the champion to ban/pick
        return data
        
    async def pick_champion(self,champion):
        #TODO: MAKE IT SO HOVERED CHAMPION WON'T BE REMOVED
        """
        @return:
            - returns a tuple of the selectUrl and banData
        """
        if type(champion) != int:
            champion = self.champion_by_name(champion)

        await self.hover_champion(champion)
        uri =  f"/lol-champ-select/v1/session/actions/{self.currentActionData['id']}/complete"
        return await self.session.request('post',uri)

    async def ban_champion(self,champion:Union[str,int]):
        if type(champion) != int:
            champion = self.champion_by_name(champion)
        
        await self.select_champion(champion)
        uri = f"/lol-champ-select/v1/session/actions/{self.currentActionData['id']}/complete"
        return await self.session.request('post',uri)


    async def champion_select_session(self):
        """
        Get data about the current champion select session.
        404: Not in champion select.
        """
        uri = "/lol-champ-select/v1/session"
        data = await self.external_get(uri)
        return data



    @property
    def current_phase(self):
        """
        Returns the current phase according to the timer
        Timer Phases:
            - PLANNING
            - BAN_PICK (ban, ten_bans_reveal)
            - FINALIZATION
        """
        
        return self.sessionData.data['timer']['phase']
        

    @property
    def is_planning_phase(self) -> bool:
        """
        Checks if it's planning phase
        """
        if self.current_phase == "PLANNING":
            return True
        
        return False

    @property
    def is_banning_phase(self) -> bool:
        """
        checks if it's banning phase
        """
        data = self.sessionData.data
        for phaseData in data['actions'][0]:
            if not phaseData['completed'] and phaseData['isInProgress']:
                return True

        return False


    @property
    def is_picking_phase(self) -> bool:
        """
        checks if it's picking phase
        """
        if self.sessionData.data['timer']['phase'] == 'BAN_PICK':
            for phaseData in self.sessionData.data['actions'][2:7]:
                if phaseData[0]['isInProgress']:
                    return True

        return False
    
    @property
    def is_final_phase(self) -> bool:
        """
        check if it's the final phase for the champion select
        """
        if self.current_phase== 'FINALIZATION':
            return True

        return False


    @property
    def is_local_player_turn(self) -> bool:
        """
        Checks if it's the local summoner's turn or not.
        """
        for actions in self.sessionData.data['actions']:
            for actionData in actions:
                if actionData['isInProgress'] and actionData['actorCellId'] == self.sessionData.data['localPlayerCellId']:
                    return True


        return False
    
