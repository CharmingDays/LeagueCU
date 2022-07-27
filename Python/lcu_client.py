import typing
import time
import base64
import os,json
from datetime import datetime
import subprocess
import sys
import pkg_resources
def check_and_install_requests():
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
       

check_and_install_requests()
import requests as rq
from requests import Response


class LCU(object):
    def __init__(self):
        self.lockfile_setup()
        self.headers={'Authorization':f"Basic {self.token}",'Accept': 'application/json'}
        self.session=rq.Session()
        # self.session.verify=os.path.join(os.path.dirname(os.path.abspath(__file__)),'riotgames.pem')
        self.riotgames_SSL()
        self.session.headers=self.headers


    def lockfile_setup(self,filePath:str=None):
        """
        Look for the lockfile and setup token and url from lockfile.
        NOTE: THE CLASS WON'T BE ABLE TO MAKE REQUESTS WITHOUT THE LOCKFILE SETUP
        """
        lockfile = r'C:\Riot Games\League of Legends\lockfile'
        if filePath:
            lockfile = filePath

        if not os.path.exists(lockfile):
            raise FileExistsError(lockfile)
        else:
            lockfile = open(lockfile,'r')
        rawData = lockfile.read()
        lockfile.close()
        rawData = rawData.split(":")
        data = {"port":rawData[2],"auth":rawData[3],"method":rawData[4]+"://127.0.0.1"}
        token = base64.b64encode(f'riot:{data["auth"]}'.encode()).decode()
        url = f"{data['method']}:{data['port']}"
        setattr(self,'token',token)
        setattr(self,'url',url)


    def riotgames_SSL(self):
        """
        sets the root certificate for the requests
        Downloads and creates one if it doesn't exist in current working dir
        """
        if 'riotgames.pem' not in os.listdir():    
            cert = self.session.get('https://gist.githubusercontent.com/CharmingDays/6e7d673403439b697b10a2d6100e2288/raw/ff15e0765da4a4d71b73b673cffb20e7d5461a64/riotgames.pem')
            current_dir = os.getcwd()
            with open('riotgames.pem','w',encoding='utf-8') as pemFile:
                pemFile.write(cert.text)
                pemFile.close()
            self.session.verify = r"{}\riotgames.pem".format(os.getcwd())

        else:
            self.session.verify = r"{}\riotgames.pem".format(os.getcwd())


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
        lobby_data=self.session.post(url,headers=self.headers,data=json.dumps(payload))
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

    def change_icon(self,iconId):
        """
        Change your summoner icon.
        """
        url = self.url+f"/lol-summoner/v1/current-summoner/icon"
        data = self.session.put(url,data=json.dumps({"profileIconId":iconId}))

        return data.ok


    def queue_check(self):
        """
        Check if a match has been found.
        """
        url = self.url+ "/lol-matchmaking/v1/ready-check"
        data= self.session.get(url)
        return data



    def play_again(self):
        #Play the same game mode again, returns back into lobby
        url = self.url+'/lol-lobby/v2/play-again'
        data = self.session.post(url)
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
        # count down timer for match found??
        #This function should return bool to indicate if there's a penalty.
        url = self.url + '/lol-lobby/v2/lobby/matchmaking/search-state'
        data = self.session.get(url).json()
        return data['lowPriorityData']['penaltyTimeRemaining']


    def start_match(self):
        self.find_match()



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
        url = self.url + "/lol-lobby-team-builder/v1/ready-check/decline"
        data = self.session.post(url)
        return data



    def accept_match(self):
        #accept match when found
        url = self.url+"/lol-matchmaking/v1/ready-check/accept"
        data  = self.session.post(url)
        return data


    def champs(self):
        return self.session.get(self.url+"/lol-champ-select/v1/pickable-champions")


    def champion_select_timer(self):
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
        url = self.url+"/lol-champ-select/v1/pickable-champion-ids"
        data = self.session.get(url)
        return data

    def hover_champion(self,championId:int):
        """
        Context:
        {
            "actorCellId": 1,
            "championId": 33,
            "completed": true,
            "id": 1,
            "isAllyAction": true,
            "isInProgress": false,
            "pickTurn": 1,
            "type": "pick"
        }
        """
        phaseData = self.check_action_turn()
        if not phaseData:
            #Indicates it's not local player's turn or all actions have been completed.
            return False
        actionId = phaseData['id']
        phaseData['championId'] = championId
        selectUrl = self.url+f'/lol-champ-select/v1/session/actions/{actionId}'
        data = self.session.patch(selectUrl,data=json.dumps(phaseData)) #Hover the champion to ban/pick
        return data
        
    def ban_pick_champion(self,champion) -> Response:
        """
        @return:
            - returns a tuple of the selectUrl and banData
        """
        if type(champion) != int:
            nameData = rq.get('https://gist.githubusercontent.com/CharmingDays/6e7d673403439b697b10a2d6100e2288/raw/ff15e0765da4a4d71b73b673cffb20e7d5461a64/champid.json').json()
            nameData = {key.upper(): value for key,value in nameData.items()}
            if champion.upper() not in nameData:
                raise f"Champion {champion} not found"
            champion = int(nameData[champion.upper()])

        self.hover_champion(champion)
        phaseData = self.check_action_turn()
        url = self.url + f"/lol-champ-select/v1/session/actions/{phaseData['id']}/complete"
        self.session.post(url)

    def champion_select_session(self):
        """
        404: Not in champion select.

        """
        url = self.url + "/lol-champ-select/v1/session"
        data = self.session.get(url)
        return data



    def check_action_turn(self) -> dict:
        """
        Returns the current incomplete phase of the action
        False if latest action already completed
        """
        data = self.champion_select_session().json()
        if not data['actions'][-1][0]['completed']:
            return data['actions'][-1][0]

        return False


    def my_turn_pick(self) -> bool:
        """
        Checks if it's the local summoner's turn or not.
        """
        data = self.champion_select_session().json()
        if data['actions'][-1][0]['actorCellId'] == data['localPlayerCellId'] and not data['actions'][-1][0]['completed']:
            return True

        return False
    
    def current_champ_select_phase(self) -> str:
        """
        Returns the current champion select phase
        """
        data = self.champion_select_session().json()
        return data['actions'][-1][0]['type']


    def export_friends(self,path=None):
        """
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


    def queue_info(self):
        queueState = self.queue_check()
        if queueState.status_code == 200:
            data = self.session.get(self.url+'/lol-matchmaking/v1/search')
            return data
        
        return False

    def bannable_campions(self) -> Response:
        """
        """
        url = self.url + "/lol-champ-select/v1/bannable-champions"
        data = self.session.get(url)
        return data


    def logout(self) -> Response:
        """
        Logout the current summoner account
        """
        url = self.url+"/lol-login/v1/session"
        data = self.session.delete(url)
        return data


    @property
    def game_state(self) -> bool:
        #Check if state of game.
        try:
            self.session.get('​https://127.0.0.1:2999/liveclientdata/activeplayername')
        except rq.exceptions.InvalidSchema:
            return False
        return True

 


    def check_selected_champion(self) -> Response:
        """
        Checks what champion the local summoner currently has LOCKED IN
        """
        url = self.url+"/lol-champ-select/v1/current-champion"
        data = self.session.get(url)
        return data



    def gg(self,url):
        data = self.session.get(self.url+url)
        print(data.text)
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



    def auto_accept_match(self,wait_time:int=3) -> tuple[Response,bool]:
        """
        The function will not work if the lobby isn't in queue already and will stop when queue has been cancelled
        - wait_time
            - amount in seconds to wait before function starts.
        """
        time.sleep(wait_time)
        if self.champion_select_session().ok or self.game_state:
            #summoner not in lobby or in queue.
            return False

        matchmaking_state = self.search_state()
        if matchmaking_state.json()['searchState'] == "Searching":
            match_found = self.queue_check().json()['state']
            while match_found == 'Invalid':
                time.sleep(.3)
                match_found = self.queue_check().json()['state']
            return self.accept_match()

        
        return matchmaking_state


    def auto_ban_champion(self,championName):
        #NOTE: DOES NOT CHECK IF USER'S TURN IS ALREADY COMPLETED OR NOT
        while not self.my_turn_pick():
            time.sleep(.2)
        
        self.ban_pick_champion(championName)

    def auto_pick_champion(self,championName):
        #NOTE: DOES NOT CHECK IF USER'S TURN IS ALREADY COMPLETED OR NOT
        while not self.my_turn_pick() and self.current_champ_select_phase() == 'pick':
            time.sleep(.2)
        self.ban_pick_champion(championName)


autos = AutoFunctions()
lol = LCU()
lol.create_lobby("ranked",'bottom','middle')