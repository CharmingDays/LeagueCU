from .riotfiles import RiotFiles
from requests import Response
from typing import Union
import json

class Chat(RiotFiles):
    def __init__(self) -> None:
        super().__init__()


    def find_summoner(self,name:str):
        url = f'/lol-summoner/v1/summoners?name={name}'
        data =  self.session.get(self.url+url)
        return data


    def send_message(self,summonerName,message:str):
        """
        Send a message to a friend
        """
        puuid = self.find_summoner(summonerName).json()['puuid']
        targetId = f'{puuid}@na1.pvp.net'
        url = self.url+f'/lol-chat/v1/conversations/{targetId}/messages'
        data = {"body": message,"id": targetId}
        return self.session.post(url,data=json.dumps(data))

