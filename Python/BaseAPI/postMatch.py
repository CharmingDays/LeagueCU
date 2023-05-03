from .riotfiles import RiotFiles
from requests import Response
from typing import Union
import json
class PostMatch(RiotFiles):
    def __init__(self) -> None:
        super().__init__()


    def get_honor_players(self) -> Union[list,bool]:
        url = '/lol-honor-v2/v1/ballot'
        data = self.session.get(self.url+url)
        if data.ok:
            return data.json()['eligiblePlayers']
        return False


    def find_honor_player(self,summonerName):
        """ 
        Return player Id in honor ballot by name
        """
        data = self.get_honor_players()
        if data:
            for player in data:
                if player['summonerName'] == summonerName:
                    return player['summonerId']
        return False

    def honor_player(self,summoner:Union[int,str],honorType="heart") -> Union[Response,bool]:
        """
        honor a player given summoner name
        """
        ballot= self.honor_player()
        url = '/lol-honor-v2/v1/honor-player'
        if ballot:
            data= self.session(self.url+url,data=json.dumps({"gameId": 0,"honorCategory": "string","summonerId": 0}))
            if data.ok:
                return data


        return False
         