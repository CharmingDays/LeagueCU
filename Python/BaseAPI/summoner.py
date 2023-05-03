import datetime
import os
import subprocess
import time
from .riotfiles import RiotFiles
from requests import Response
from typing import Union
import json
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

