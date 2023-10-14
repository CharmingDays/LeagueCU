from .riotfiles import RiotFiles
import json
from lcu_driver.connector import Connection
from lcu_driver.events.responses import WebsocketEventResponse as EventResponse
class Lobby():
    def __init__(self) -> None:
        self.session:Connection
        self.data:EventResponse

    def updateData(self,connection:Connection,data:EventResponse):
        self.session = connection
        self.data = data
    
    
    async def lobby_data(self):
        uri ='/lol-lobby/v2/lobby'
        response = await self.session.request('get',uri)
        return response


    @property
    def members_has_roles(self):
        """
        Checks to see if all members in lobby has roles selected.
        True if all has roles else False
        """
        data = self.lobby_data().json()
        for member in data['members']:
            if member['firstPositionPreference'] == 'UNSELECTED' or member['secondPositionPreference'] == 'UNSELECTED':
                return False
        
        return True


    @property
    def ready_to_start(self):
        """
        Lobby is ready to find match
        """
        return self.lobby_data().json()['canStartActivity']

    
    @property
    def is_room_owner(self):
        return self.lobby_data().json()['localMember']['isLeader']


    @property
    def summoner_positions(self) -> str:
        """
        @return
        first,second
        """
        localMem= self.lobby_data().json()['localMember']
        return localMem['firstPositionPreference'], localMem['secondPositionPreference']


    def play_again(self):
        #Play the same game mode again, returns back into lobby
        url = self.url+'/lol-lobby/v2/play-again'
        data = self.session.post(url)
        return data


    def leave_lobby(self):
        """
        Leaves the lobby
        NOTE: DO NOT RUN THIS FUNCTION WHILE STILL DURING THE HONOR TEAMMATE SCREEN TO AVOID BLACK SCREEN
        """
        url=self.url+"/lol-lobby/v2/lobby"
        data = self.session.delete(url)
        return data
    
    async def start_lobby(self):
        uri = '/lol-lobby/v1/lobby/custom/start-champ-select'
        response =await self.session.request('post',uri)
        return response


    async def create_lobby(self,queue_type:str="DRAFT",primaryRole = None, secondaryRole = "FILL"):
        """
        Create a lobby with given lobby type
        Check the `queue_dict` dict for lobby options
        THIS FUNCTION CAN ALSO SET THE ROLE POSITIONS IF PROVIDED
            - NOTE: NOT SETTING THE SECONDARY ROLE WILL MAKE YOU FILL AS SECONDARY 
        """
        queue_type= queue_type.upper()
        queue_dict= {
            "DRAFT": 400,
            "RANKED":420,
            "RANKED_FLEX":440,
            "ARAM":450,
            "BLIND":430,
            "CUSTOM":"CUSTOM_GAME",
            "PRACTICE":"PRACTICETOOL"
        }
        uri ="/lol-lobby/v2/lobby"

        if queue_type in ['CUSTOM_GAME','PRACTICE']:
            data = {
                "customGameLobby": {
                    "configuration": {
                    "gameMode": f"{queue_dict[queue_type]}", "gameMutator": "", "gameServerRegion": "", "mapId": 11, "mutators": {"id": 1}, "spectatorPolicy": "AllAllowed", "teamSize": 5
                    },
                    "lobbyName": "Name",
                    "lobbyPassword": None
                },
                "isCustom": True
            }
            return await self.session.request('post',uri,data=data)
            

        if queue_type not in queue_dict:
            return f"Queue type {queue_type} not found."

        payload={
            "queueId": queue_dict[queue_type]
        }
        lobby_data=await self.session.request('post',uri,data=payload)
        if primaryRole:
            self.role_position(primaryRole,secondaryRole)
        return lobby_data



    def role_position(self,primary="FILL",secondary="FILL"):
        """
        Change the role for the lobby
        Position names:
            - TOP, BOTTOM, SUPPORT, JUNGLE, MIDDLE
        primary: FILL
            - your primary role for the game queue
        secondary: FILL
            - your secondary role for the game queue 
        """
        url=self.url+"/lol-lobby/v2/lobby/members/localMember/position-preferences"
        primary,secondary = primary.upper(),secondary.upper()
        payload={
            "firstPreference": primary,
            "secondPreference": secondary
        }
        position_data=self.session.put(url,data=json.dumps(payload))
        return position_data

    def send_invite(self,summoner_name:str):
        """
        Invite a summoner to your lobby
        """
        summoner_url=self.url+f"/lol-summoner/v1/summoners?name={summoner_name}"
        summoner_data=self.session.get(summoner_url)
        
        if summoner_data.status_code == 404:
            return f"Summoner {summoner_name} not found"
        
        summonerId=summoner_data.json()['summonerId']
        invite_url=self.url+'/lol-lobby/v2/lobby/invitations'
        payload=[{
            "toSummonerId":summonerId
        }]

        invite_data=self.session.post(invite_url,data=json.dumps(payload))

        return invite_data
