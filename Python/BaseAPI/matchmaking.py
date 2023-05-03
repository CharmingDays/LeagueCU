from .riotfiles import RiotFiles
from requests import Response
from typing import Union
import json
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
        data = self.search_state()
        if data.ok and  data.json()['searchState'] == 'Found':
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

