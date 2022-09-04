from functools import cached_property
from http.client import INTERNAL_SERVER_ERROR
import time
import base64
import os,json
from datetime import datetime
import subprocess
import sys
from xml.etree.ElementPath import prepare_parent, prepare_predicate
import pkg_resources
import random
def check_and_install_requirements():
    #INSTALLS MISSING LIBS IF NOT FOUND
    required = {'requests'}
    installed = {pkg.key for pkg in pkg_resources.working_set}
    missing = required - installed
    if missing:
        print("modules {} are missing".format(*missing))
        python = sys.executable
        subprocess.check_call([python,'-m','pip','install',*missing],stdout=subprocess.DEVNULL)
        print("New modules were installed, please try restarting the script if it doesn't work.")
        time.sleep(5)
       

check_and_install_requirements()
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
        data = rq.get('https://gist.githubusercontent.com/CharmingDays/6e7d673403439b697b10a2d6100e2288/raw/ff15e0765da4a4d71b73b673cffb20e7d5461a64/champid.json')
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
    def local_player_cell_data(self):
        """
        Returns the current local player's cell data that is in progress
        """
        sessionData = self.champion_select_session().json()
        for data in sessionData['actions']:
            for innerData in data:
                if innerData['isInProgress'] and innerData['actorCellId'] == sessionData['localPlayerCellId']:
                    return innerData

        return False


    def hover_data(self,data):
        """
        Returns the local player's data for picking phase, mainly looking for the "id" from actions in pick phase
        """
        #get the summoner's pick id
        for i in data['actions']:
            for inner in i:
                if inner['type'] == 'pick' and inner['completed'] is False and inner['actorCellId'] == data['localPlayerCellId']:                    
                    return inner


    @property
    def selected_champion(self):
        """
        returns the currently selected champion
        """
        data = self.hover_data(self.champion_select_session().json())
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
        #NOTE: CLICKING ON A CHAMPION MANUALLY WILL TAKE CONTROL OVER AND THIS WILL NOT WORK ANYMORE
        #NOTE: THIS SHOULD BE USED ONLY TO BAN/PICK CHAMPIONS
        data = self.champion_select_session().json()
        hoverData = self.hover_data(data)

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
        #TODO: SHOULD CHECK IF CHAMPION TO LOCK IS SAME AS HOVERED CHAMPION
        """
        @return:
            - returns a tuple of the selectUrl and banData
        """
        if type(champion) != int:
            champion = self.champion_by_name(champion)

        self.hover_champion(champion)
        url = self.url + f"/lol-champ-select/v1/session/actions/{self.local_player_cell_data['id']}/complete"
        self.session.post(url)

    def champion_select_session(self):
        """
        Get data about the current champion select session.
        404: Not in champion select.
        """
        url = self.url + "/lol-champ-select/v1/session"
        data = self.session.get(url)
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
        url = self.url + "/lol-champ-select/v1/session"
        data = self.session.get(url)
        if data.status_code.ok:
            return data.json()['timer']['phase']
        
        return data.status_code
        

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
        data = data.json()
        if data['timer']['phase'] == "BAN_PICK":
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
        data = data.json()
        if data['timer']['phase'] == 'BAN_PICK':
            for phaseData in data['actions'][2:7]:
                if phaseData['isInProgress']:
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
        data = self.champion_select_session().json()
        if self.local_player_cell_data['isInProgress']:
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



    def change_icon(self,iconId):
        """
        Change your summoner icon.
        """
        url = self.url+f"/lol-summoner/v1/current-summoner/icon"
        data = self.session.put(url,data=json.dumps({"profileIconId":iconId}))

        return data.ok


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


    def queue_check(self):
        """
        Check if a match has been found.
        """
        url = self.url+ "/lol-matchmaking/v1/ready-check"
        data= self.session.get(url)
        return data


    def search_state(self) -> Response:
        """
        Check the state of the match search
        Invalid: Not in queue
        Searching: In queue for match.
        """
        url = self.url+ "/lol-lobby/v2/lobby/matchmaking/search-state"
        data = self.session.get(url)
        return data


    def penalty_countdown(self):
        #NOTE: THIS IS ONLY FOR LEAVERBUSTER AND LOWER QUEUE PRIO
        # count down timer for match found??
        #This function should return bool to indicate if there's a penalty.
        url = self.url + '/lol-lobby/v2/lobby/matchmaking/search-state'
        data = self.session.get(url).json()
        return data['lowPriorityData']['penaltyTimeRemaining']


    def start_match(self):
        #alias for match
        self.find_match()


    def leave_queue(self):
        """
        Leave the current queue 
        """
        url = self.url+"/lol-lobby/v2/lobby/matchmaking/search"
        data = self.session.delete(url)
        return data



    def find_match(self):
        """
        Start the queue for the lobby.


        ERRORS:
            BAD_METADATA: No positions selected
            INVALID_POSITION_PREFERENCES: Only one role selected and maybe party member do not cover enough roles.
        """
        url = self.url+"/lol-lobby/v2/lobby/matchmaking/search"
        data = self.session.post(url)
        return data


    def decline_match(self):
        url = self.url + "/lol-matchmaking/v1/ready-check/decline"
        data = self.session.post(url)
        return data



    def accept_match(self):
        #accept match when found
        url = self.url+"/lol-matchmaking/v1/ready-check/accept"
        data  = self.session.post(url)
        return data

    def queue_info(self):
        queueState = self.queue_check()
        if queueState.status_code == 200:
            data = self.session.get(self.url+'/lol-matchmaking/v1/search')
            return data
        
        return False




class LiveGameData(object):
    """
    Doc for this API can be found here: https://developer.riotgames.com/docs/lol#game-client-api_live-client-data-api
    """
    def __init__(self) -> None:
        pass
    @property
    def game_state(self) -> bool:
        #Checks if the local player's game has started
        try:
            self.session.get('​https://127.0.0.1:2999/liveclientdata/activeplayername')
        except rq.exceptions.InvalidSchema:
            return False
        return True

 



class LCU(Lobby,ChampSelect,Summoner,LiveGameData):
    """
    Docs for LCU can be found here: 
        https://lcu.vivide.re/
        https://github.com/Remlas/lolcup-tools/blob/master/AllRequests.txt

    """
    def __init__(self):
        super().__init__()


    def play_again(self):
        #Play the same game mode again, returns back into lobby
        url = self.url+'/lol-lobby/v2/play-again'
        data = self.session.post(url)
        return data


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



    def auto_accept_match(self) -> Response:
        """
        The function will not work if the lobby isn't in queue already and will stop when queue has been cancelled
        """
        #SUMMONER NOT IN LOBBY
        if self.queue_check().status_code == 404:
            return False

        matchmaking_state = self.search_state()
        if matchmaking_state.json()['searchState'] == "Searching":
            while self.queue_check().json()['state'] == 'Invalid':
                time.sleep(.3)
            return self.accept_match()

        
        return matchmaking_state


    def auto_ban_champion(self,championName):
        #NOTE: DOES NOT CHECK IF USER'S TURN IS ALREADY COMPLETED OR NOT
        while not self.is_local_player_turn:
            time.sleep(.2)
        
        self.ban_pick_champion(championName)



    def auto_pick_champion(self,champion:list):
        #NOTE: DOES NOT CHECK IF USER'S TURN IS ALREADY COMPLETED OR NOT
        #TODO: ALLOW RECOMMENDED SELECTION IF ALL CHAMPIONS GIVEN BY USER IS BANNED
        while self.champion_select_session().ok:
            if self.current_champ_select_phase == 'pick':
                if self.is_local_player_turn:
                    championNames = self.champion_by_name(champion) #convert ids to names 
                    pickableChamps= self.pickable_champions().json()
                    for champ in championNames:
                        if champ in pickableChamps:
                            return self.ban_pick_champion(champ)
                    
            time.sleep(.2)
        self.ban_pick_champion(champion)



lol = LCU()
auto = AutoFunctions()