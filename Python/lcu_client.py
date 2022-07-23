import requests as rq
from requests import Response
import time
import base64
import lcu_connector_python as lcu
import os,json
from datetime import datetime
from lcu_driver import Connector
import keyboard

class LCU(object):
    def __init__(self):
        self._local=lcu.connect()
        self.token=base64.b64encode(f'riot:{self._local["authorization"]}'.encode()).decode()
        self.url="https://"+self._local['url']
        self.headers={'Authorization':f"Basic {self.token}",'Accept': 'application/json'}
        self.session=rq.Session()
        # self.session.verify=os.path.join(os.path.dirname(os.path.abspath(__file__)),'riotgames.pem')
        self.riotgames_SSL()
        self.session.headers=self.headers
        self.fullBanPosition=1


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
        url=self.url+"/lol-lobby/v2/lobby"
        data = self.session.delete(url)
        return data
    
    def create_lobby(self,queue_type:str="DRAFT"):
        """
        Create a lobby with given lobby type
        Check the `queue_dict` dict for lobby options
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
        data = True if data['state']  == 'InProgress' else False #NOTE: NOT TESTED
        return data


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


    def accept_match(self):
        #accept match when found
        url = self.url+"/lol-matchmaking/v1/ready-check/accept"
        data  = self.session.post(url)
        return data


    def champs(self):
        return self.session.get(self.url+"/lol-champ-select/v1/pickable-champions")


    def champion_select_timer(self):
        url = self.url+f"/lol-champ-select/v1/session/timer"
        data = self.session.get(url)
        return data.text

    def locked_in_champion(self):
        url = self.url+'/lol-champ-select/v1/current-champion'
        data = self.session.get(url)
        return data

    def banable_champions(self):
        url = self.url+"/lol-champ-select/v1/bannable-champion-ids"
        data = self.session.get(url)
        return data

    def pickable_champions(self):
        url = self.url+"/lol-champ-select/v1/pickable-champion-ids"
        data = self.session.get(url)
        return data


    def ban_champion(self,championId,fullBan:bool=False):
        """
        fullBan:
            - indicate whether one summoner will ban for entire team
        
        @return:
            - returns a tuple of the selectUrl and banData    
        """
        selectUrl = self.url+'/lol-champ-select/v1/session/actions/1'
        payload = {"championId":championId}

        selectData = self.session.patch(selectUrl,data=json.dumps(payload))
        banUrl = self.url+f'/lol-champ-select/v1/session/actions/{self.fullBanPosition}/complete'
        if fullBan:
            self.fullBanPosition+=1
        banData = self.session.post(banUrl)
        completeUrl = self.url + f'/lol-champ-select/v1/session/actions/{self.fullBanPosition}/complete'
        self.session.post(completeUrl)
        return selectData,banData


    def champion_select_session(self):
        url = self.url + "/lol-champ-select/v1/session"
        data = self.session.get(url)
        return data


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


    def logout(self):   
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






    def auto_accept_match(self,wait_time=3) -> Response:
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


lol = LCU()
autos = AutoFunctions()