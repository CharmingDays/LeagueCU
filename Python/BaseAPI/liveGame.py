from .riotfiles import RiotFiles
from requests import Response
from typing import Union
import json
import requests as rq
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

