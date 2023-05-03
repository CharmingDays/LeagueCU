from .riotfiles import RiotFiles
from requests import Response
from typing import Union
import json
class ChampSelect(RiotFiles):
    """
    Champion select methods for the LCU
    """
    def __init__(self) -> None:
        super().__init__()

    def champion_select_timer(self):
        #NOTE: INCOMPLETE
        url = self.url+f"/lol-champ-select/v1/session"
        data = self.session.get(url)
        return data.json()['timer']

    def locked_in_champion(self):
        url = self.url+'/lol-champ-select/v1/current-champion'
        data = self.session.get(url)
        return data


    def hovered_ban(self):
        """
        Return the current hovered ban intent champion ID. 0 if none
        """
        local = self.local_player_cell_data
        if local:
            return local['championId']

        return False

    def bannable_champions(self):
        """
        Returns a list of bannable champion ids
        """
        url = self.url+"/lol-champ-select/v1/bannable-champion-ids"
        data = self.session.get(url)
        return data

    def pickable_champions(self) -> Response:
        """
        Get the current pickable champions in session
        """
        url = self.url+"/lol-champ-select/v1/pickable-champion-ids"
        data = self.session.get(url)
        return data

    @property
    def local_player_cell_id(self):
        """
        Returns the localPlayerCellId which is used to identify user's actions.
        """
        data= self.champion_select_session()
        return data.json()['localPlayerCellId']


    @property
    def player_position(self,cellId=None):
        """
        Position of local player or of given cellId
        """
        if cellId is None:
            cellId = self.local_player_cell_id
            return self.local_player_team_data['assignedPosition']

        team = self.team_data()
        for playerData in team:
            if playerData['cellId'] == cellId:
                return playerData['assignedPosition']
            
            

    @property
    def local_player_team_data(self):
        """
        Returns team data of local player
        """
        data = self.champion_select_session().json()
        team = data['myTeam']
        localId = self.local_player_cell_id
        for i in team:
            if i['cellId'] == localId:
                return i

    def team_data(self):
        """
        Returns the team data
        """
        data =self.champion_select_session().json()
        team = data['myTeam']
        return team


    def hovered_champions(self):
        """
        Returns a list of champions that team has hovered
        """
        team = self.team_data()
        champions= []
        for playerData in team:
            if playerData['championPickIntent'] !=0:
                champions.append(playerData['championPickIntent'])
        
        return champions

    @property
    def local_player_cell_data(self):
        """
        Returns the current local player's cell data that is in progress
        """
        sessionData = self.champion_select_session().json()
        for data in sessionData['actions']:
            for innerData in data:
                if innerData['isInProgress'] and innerData['actorCellId'] == sessionData ['localPlayerCellId']:
                    return innerData


        return False


    def get_phase_data(self,actorCellId:int,phase:str):
        """
        """
        champData = self.champion_select_session().json()
        for data in champData['actions']:
            for actorData in data:
                if actorData['actorCellId'] == actorCellId and actorData['type'] == phase:
                    return actorData

    def hover_data(self):
        """
        Returns the local player's data for picking phase, mainly looking for the "id" from actions in pick phase
        """
        #get the summoner's pick id
        _data = self.champion_select_session()
        print(_data.text)
        data = _data.json()
        for i in data['actions']:
            for inner in i:
                if inner['type'] == 'pick' and inner['completed'] is False and inner['actorCellId'] == data['localPlayerCellId']:                    
                    return inner


    @property
    def selected_champion(self):
        """
        returns the currently selected champion
        """
        data = self.hover_data()
        return data['championId']

    def champion_by_name(self,champion):
        """
        Returns the id of the champion by name
        """
        championNames = {key.upper(): value for key,value in self.champion_names.items()}
        if champion.upper() not in championNames:
            raise f"Champion {champion} not found"
        return int(championNames[champion.upper()])


    def hover_champion(self,champion):
        """
        Hover the given champion
        """
        #NOTE: CLICKING ON A CHAMPION MANUALLY WILL TAKE CONTROL OVER AND THIS WILL NOT WORK ANYMORE
        #NOTE: THIS SHOULD BE USED ONLY TO BAN/PICK CHAMPIONS
        #NOTE: for ban/pick phase
        hoverData = self.hover_data()
        print(hoverData)
        url = self.url + f'/lol-champ-select/v1/session/actions/{hoverData["id"]}'
        if type(champion) != int:
            champion = self.champion_by_name(champion)
        hoverData['championId'] = champion
        return self.session.patch(url,data=json.dumps(hoverData))


    def select_champion(self,championId):
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
        phaseData =  self.local_player_cell_data #the player pick data
        #change the values to local player's 
        phaseData['championId'] = championId
        selectUrl = self.url+f'/lol-champ-select/v1/session/actions/{phaseData["id"]}'
        data = self.session.patch(selectUrl,data=json.dumps(phaseData)) #Hover the champion to ban/pick
        return data
        
    def pick_champion(self,champion) -> Response:
        #TODO: MAKE IT SO HOVERED CHAMPION WON'T BE REMOVED
        """
        @return:
            - returns a tuple of the selectUrl and banData
        """
        if type(champion) != int:
            champion = self.champion_by_name(champion)

        self.hover_champion(champion)
        url = self.url + f"/lol-champ-select/v1/session/actions/{self.local_player_cell_data['id']}/complete"
        return self.session.post(url)

    def ban_champion(self,champion:Union[str,int]) -> Union[Response,dict]:
        if type(champion) != int:
            champion = self.champion_by_name(champion)
        
        self.select_champion(champion)
        url = self.url + f"/lol-champ-select/v1/session/actions/{self.local_player_cell_data['id']}/complete"
        return self.session.post(url)


    def champion_select_session(self):
        """
        Get data about the current champion select session.
        404: Not in champion select.
        """
        url = self.url + "/lol-champ-select/v1/session"
        data = self.session.get(url)
        return data


    @property
    def in_champion_select(self):
        """
        Check if client is in champion select
        Property alias of champion_select_session
        """
        if self.champion_select_session().ok:
            return True
        return False


    @property
    def current_phase(self):
        """
        Returns the current phase according to the timer
        Timer Phases:
            - PLANNING
            - BAN_PICK (ban, ten_bans_reveal)
            - FINALIZATION
        """
        data = self.champion_select_session()
        if data.ok:
            return data.json()['timer']['phase']
        
        return False
        

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
        data = self.champion_select_session()
        if data.ok and data.json()['timer']['phase'] == "BAN_PICK":
            data = data.json()
            for phaseData in data['actions'][0]:
                if phaseData['isInProgress']:
                    return True

        return False


    @property
    def is_picking_phase(self) -> bool:
        """
        checks if it's picking phase
        """

        data = self.champion_select_session()
        if data.ok and data.json()['timer']['phase'] == 'BAN_PICK':
            data = data.json()
            for phaseData in data['actions'][2:7]:
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



    def current_actor(self,phase=None) -> dict:
        #TODO:
        #NOTE: NEEDS TO BE REMADE
        """
        Returns the current phase data as list
        False if latest action already completed
        """
        data = self.champion_select_session()
        if data.status_code == 404:
            return data.status_code
        data = data.json()
        for actions in data['actions']:
            for actionData in actions:
                if actionData['isInProgress']:
                    return actions

        return False

    @property
    def is_local_player_turn(self) -> bool:
        """
        Checks if it's the local summoner's turn or not.
        """
        data= self.champion_select_session().json()
        for actions in data['actions']:
            for actionData in actions:
                if actionData['isInProgress'] and actionData['actorCellId'] == data['localPlayerCellId']:
                    return True


        return False
    

    def locked_in_champion(self) -> Response:
        """
        Checks what champion the local summoner currently has LOCKED IN
        0: No champion locked in
        """
        url = self.url+"/lol-champ-select/v1/current-champion"
        data = self.session.get(url)
        return data


