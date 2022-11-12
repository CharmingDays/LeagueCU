import random
import time
import base64
import os,json
from datetime import datetime
import subprocess
from typing import Union,List
import requests as rq
from requests import Response


class RiotFiles(object):
    """
    Class for dealing with riotgames' files and other external files for LCU
        - lockfile: the file containing the port, login, http method
        - riotgames.pem: the file containing the SSL certification for making the https requests
    """
    def __init__(self) -> None:
        self.session = rq.Session()
        self.lockfile()
        self.riotgames_SSL()
        self.session.headers = {'Authorization':f"Basic {self.token}",'Accept': 'application/json'}
        self.champion_names = {}
        self.get_champion_names()


    def get_champion_names(self):
        #TODO: use data dragon champions instead -> http://ddragon.leagueoflegends.com/cdn/{patch_version}/data/en_US/champion.json
        data = rq.get('https://gist.githubusercontent.com/CharmingDays/6e7d673403439b697b10a2d6100e2288/raw/88e3bbaf1b095fd2aac74189a80d2b5f41bd859b/champid.json')
        if data.ok:
            self.champion_names = data.json()
            return True
        return False


    def refresh_champion_names(self,newUrl):
        data = rq.get(newUrl)
        if data.ok:
            self.champion_names = data.json()
            return True

        return False
        


    def lockfile(self,filePath:str=None):
        """
        Look for the lockfile and setup token and url from lockfile.
        NOTE: THE CLASS WON'T BE ABLE TO MAKE REQUESTS WITHOUT THE LOCKFILE SETUP
        """
        defaultLockfile = r'C:\Riot Games\League of Legends\lockfile'
        if filePath:
            # set the filePath param to value of defaultLockfile if argument for filePath not given
            defaultLockfile = filePath

        if not os.path.exists(defaultLockfile):
            # lock file doesn't exist in default defaultLockfile path
            raise FileExistsError(defaultLockfile)
        else:
            defaultLockfile = open(defaultLockfile,'r')
        rawData = defaultLockfile.read()
        defaultLockfile.close()
        rawData = rawData.split(":") # convert to list
        data = {"port":rawData[2],"auth":rawData[3],"method":rawData[4]+"://127.0.0.1"} #turn into dict
        token = base64.b64encode(f'riot:{data["auth"]}'.encode()).decode()
        url = f"{data['method']}:{data['port']}"
        # set class attributes
        setattr(self,'token',token)
        setattr(self,'url',url)


    def riotgames_SSL(self):
        """
        sets the root certificate for the requests
        Downloads and creates one if it doesn't exist in current working dir
        """
        current_dir = os.getcwd()
        if 'riotgames.pem' not in os.listdir():
            #retrieve the SSL cert from github gist
            cert = self.session.get('https://gist.githubusercontent.com/CharmingDays/6e7d673403439b697b10a2d6100e2288/raw/ff15e0765da4a4d71b73b673cffb20e7d5461a64/riotgames.pem')
            with open('riotgames.pem','w',encoding='utf-8') as pemFile:
                pemFile.write(cert.text)
                pemFile.close()
            self.session.verify = r"{}\riotgames.pem".format(current_dir)

        else:
            self.session.verify = r"{}\riotgames.pem".format(current_dir)


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
        data = self.champion_select_session().json()
        for i in data['actions']:
            for inner in i:
                if inner['type'] == 'pick' and inner['completed'] is False and inner['actorCellId'] == data['localPlayerCellId']:                    
                    return inner


    def hovered_champions(self):
        """
        Returns a list of champions that are hovered by allies
        """
        data = self.champion_select_session().json()
        hoveredChampions = []
        for actions in data['actions']:
            for actionData in actions:
                if actionData['type'] == 'pick' and actionData['completed'] is False:
                    if actionData['championId'] != 0: #champion intent is shown
                        hoveredChampions.append(actionData['championId'])

        return hoveredChampions
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
        hoverData = self.hover_data()

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
        
    def ban_pick_champion(self,champion) -> Response:
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





class Summoner(RiotFiles):
    def __init__(self) -> None:
        super().__init__()

    def summoner_info(self):
        url = self.url+'/lol-summoner/v1/current-summoner'
        data = self.session.get(url)
        return data

    def change_icon(self,iconId):
        """
        Change your summoner icon.
        """
        url = self.url+"/lol-summoner/v1/current-summoner/icon"
        data = self.session.put(url,data=json.dumps({"profileIconId":iconId}))

        return data.ok

    def add_friend(self,summonerName:str) -> Response:
        #TODO: MAKE ADD FRIEND FUNCTION
        url = self.url+ ''
        data = self.session.get(url,data=json.dumps({'name':summonerName}))
        return data

    def export_friends(self,path=None):
        """
        Exports your friends' list into a json file format
        - path
            - NOTE: MAKE SURE THE DIRECTORY EXISTS ELSE IT WON'T WORK
            - the path to save the file containing friend names
            - DEFAULT path will be the location of the application
            - Do not include quotation marks when entering the path
        """
        url = self.url+ "/lol-game-client-chat/v1/buddies"
        data = self.session.get(url)
        if path is None:
            path = os.getcwd()

        with open(f"{path}\League_of_Legends_friends_{datetime.now().date()}.txt","w",encoding="utf-8")as file:
            file.write(data.text)
            file.close()

        return data


    def logout(self) -> Response:
        """
        Logout the current summoner account
        THIS WILL NOT LOG YOU OUT OF THE RIOT CLIENT
        """
        url = self.url+"/lol-login/v1/session"
        data = self.session.delete(url)
        return data



    def closeLeague(self):
        """
        Closes the league client
        IT IS RECOMMENDED TO WAIT A FEW SECONDS (~6) AFTER RUNNING THE LOGOUT FUNCTION BEFORE CLOSING THE CLIENT
        """
        subprocess.call(["taskkill", "/f", "/im", "RiotClientServices.exe"])
        time.sleep(2)
        subprocess.call(["taskkill", "/f", "/im", "LeagueClient.exe"])


class Lobby(RiotFiles):
    def __init__(self) -> None:
        super().__init__()

    def lobby_data(self):

        return self.session.get(self.url+'/lol-lobby/v2/lobby')


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
    
    def create_lobby(self,queue_type:str="DRAFT",primaryRole = None, secondaryRole = "FILL"):
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
        url=self.url+"/lol-lobby/v2/lobby"

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
            self.session.post(url,data=json.dumps(data))
            

        if queue_type not in queue_dict:
            return f"Queue type {queue_type} not found."

        payload={
            "queueId": queue_dict[queue_type]
        }
        lobby_data=self.session.post(url,data=json.dumps(payload))
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

class Matchmaking(RiotFiles):
    """
    Matchmaking endpoints for the client
    """
    def __init__(self) -> None:
        super().__init__()

    @property
    def match_found(self) ->bool:
        """
        Checks if match is found
        """
        data = self.search_state().json()['searchState']
        if data.ok and data == 'Found':
            return True

        return False


    def ready_check(self) -> Union[Response,bool]:
        """
        queue info

        """
        url = self.url+ "/lol-matchmaking/v1/ready-check"
        data= self.session.get(url)
        if data.ok:
            return data

        return False

    
    @property
    def in_queue(self) ->bool:
        """
        Checks if client is in queue. 
        """
        #TODO: Check vs search_state
        data = self.ready_check()
        if data.ok:
            return True
        return False

    def search_state(self) -> Union[Response,bool]:
        """
        Check the state of the match search
        Invalid: Not in queue
        Searching: In queue for match.
        """
        # url = self.url+ "/lol-lobby/v2/lobby/matchmaking/search-state"
        url = self.url+ "/lol-matchmaking/v1/search"
        data = self.session.get(url)
        if data.ok:
            return data

        return False


    def start_match(self) ->Union[Response,bool]:
        """
        alias for match
        """
        self.find_match()


    def leave_queue(self) ->Union[Response,bool]:
        """
        Leave the current queue 
        """
        url = self.url+"/lol-lobby/v2/lobby/matchmaking/search"
        data = self.session.delete(url)
        if data.ok:
            return data

        return False



    def find_match(self) ->Union[Response,bool]:
        """
        Start the queue for the lobby.


        ERRORS:
            BAD_METADATA: No positions selected
            INVALID_POSITION_PREFERENCES: Only one role selected and maybe party member do not cover enough roles.
        """
        url = self.url+"/lol-lobby/v2/lobby/matchmaking/search"
        data = self.session.post(url)
        if data.ok:
            return data

        return False


    def decline_match(self) -> Union[Response,bool]:
        url = self.url + "/lol-matchmaking/v1/ready-check/decline"
        data = self.session.post(url)
        if data.ok:
            return data

        return False

    

    def accept_match(self) -> Union[Response,bool]:
        #accept match when found
        url = self.url+"/lol-matchmaking/v1/ready-check/accept"
        data  = self.session.post(url)
        if data.ok:
            return data

        return False

    def queue_info(self):
        queueState = self.ready_check()
        if queueState.status_code == 200:
            data = self.session.get(self.url+'/lol-matchmaking/v1/search')
            return data
        
        return False




class LiveGameData(RiotFiles):
    """
    Doc for this API can be found here: https://developer.riotgames.com/docs/lol#game-client-api_live-client-data-api
    """
    # TODO: Return object with class methods to ease access to data
    def __init__(self) -> None:
        super().__init__()
        self.game_data = {}

    @property
    def game_state(self) -> bool:
        #Checks if the local player's game has started
        try:
            data =self.session.get('https://127.0.0.1:2999/liveclientdata/activeplayername')
            self.game_data = data.json()
            return True
        except (rq.exceptions.InvalidSchema,rq.exceptions.ConnectionError):
            return False
    

    def refresh_data(self) -> Union[dict,bool]:
        data =self.session.get('https://127.0.0.1:2999/liveclientdata/allgamedata')
        if not data.ok:
            return False

        self.game_data = data.json()
        return self.game_data

    def player_names(self) -> list:
        """
        Get the names of all players
        """
        playerNames = []
        for _ in self.game_data['allPlayers']:
            playerNames.append(self.game_data['allPlayers']['summonerName'])
        return playerNames

    def players_summoner_spells(self):
        pass


    def player_runes(self,summonerName):
        pass

    def player_scores(self) ->dict:
        """
        Get the scores for all players
        """
        #TODO: calculate KP
        playerScores = {}
        for _ in self.game_data['allPlayers']:
            name = self.game_data['allPlayers']['summonerName']
            scores = self.game_data['allPlayers']['score']
            playerScores[name] = scores

        return playerScores 

    def random_skin(self):
        #TODO: select random skin for champion
        pass


    def hover_random_champion(self):
        #TODO: hover a random champion
        pass


    def pick_random_champion(self):
        #TODO: random champion
        pass




class LCU(Lobby,ChampSelect,Summoner,LiveGameData,Matchmaking):
    """
    Docs for LCU can be found here: 
        https://lcu.vivide.re/
        https://github.com/Remlas/lolcup-tools/blob/master/AllRequests.txt

    """
    def __init__(self):
        super().__init__()




class AutoFunctions(LCU):
    """
    A class that uses the LCU class to implement  automatic functions
    
    CURRENT FEATURES:
        - auto_accept:
            -- automatically start queue or wait until queue starts and accepts the match for you until in champion select.

        - auto_ban:
            -- automatically ban a champion from a list

        - auto_runes:
            -- automatically set runes if user has a defined runes for the selected champion.
    """
    def __init__(self):
        super().__init__()

    def convert_time(self,seconds:int) -> int:
        if seconds >= 60:
            return f"{seconds/60} minutes"
        return seconds



    def auto_champion_selection(self,champPicks:List[str],champBan:List[str]) -> Response:
        """
        Automatically select and lock in champion
        -Hover champion
        -ban champion
        -lock in champion

        """
        banAble = self.bannable_champions().json()
        actorId = self.local_player_cell_id
        while not self.game_state:
            if not self.in_champion_select:
                # prevent non scribble error.
                continue
            if self.is_planning_phase and self.local_player_team_data['championPickIntent'] == 0: #TODO: CHECK TO SEE IF USER ALREADY HOVERED CHAMPION
                #NOTE: PICK INTENT PHASE(PLANNING PHASE)
                self.hover_champion(champPicks[0])
            if self.is_banning_phase and self.get_phase_data(actorId,'ban')['completed'] is False:
                #NOTE: BANNING PHASE
                #ban phase, user has not banned
                hoveredChampions = self.hovered_champions()
                for champ in champBan:
                    champId =self.champion_by_name(champ)
                    if champId in banAble and champId not in hoveredChampions:
                        ban = self.ban_pick_champion(champ)
                        if ban.ok:
                            # ban successful
                            break

            if self.is_picking_phase and self.get_phase_data(actorId,'pick')['completed'] is False and self.is_local_player_turn:
                # Checks phase,user's turn, action status(turn completed?)
                #NOTE: PICKING PHASE - USER'S TURN
                for champ in champPicks:
                    pick = self.ban_pick_champion(champ)
                    if pick.ok:
                        # action successful
                        break
                        
            time.sleep(1)


    def auto_accept_game(self,picks=None,bans=None) -> Response:
        """
        Auto accept matches until summoner in game.
        #NOTE: DODGE NOT TESTED
        """
        # Not in game yet
        if self.is_room_owner and self.ready_to_start:
            self.find_match()

        while not self.game_state:
            #wait for game to start
            if not self.in_champion_select:
                #waiting to be in champ select
                if self.in_queue:
                    #waiting in queue
                    if self.match_found and self.ready_check().json()['playerResponse'] != "Accepted":
                        #match found and accepted
                        self.accept_match()

            if self.in_champion_select:
                if picks is None or bans is None:
                    continue
                else:
                    self.auto_champion_selection(picks,bans)
            time.sleep(1)

        return self.game_data

def write_data(func):
    data= func()
    with open("D:\\Developer\\LeagueCU\\test\\{}.json".format(func.__name__),'w',encoding='utf-8') as file:
        file.write(json.dumps(data.json()))



lol = LCU()
auto = AutoFunctions()
picks = ['missfortune','jinx']
bans = ['blitzcrank','twitch']
auto.auto_accept_game(picks,bans)