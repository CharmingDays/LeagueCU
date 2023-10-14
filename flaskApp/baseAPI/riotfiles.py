import base64
import os
import requests as rq
import json
import aiohttp
class RiotFiles(object):
    """
    Class for dealing with riotgames' files and other external files for LCU
        - lockfile: the file containing the port, login, http method
        - riotgames.pem: the file containing the SSL certification for making the https requests
    """
    def __init__(self) -> None:
        self.champion_ids = {}
        self.champion_names = {}
        self.__dd_version()
        self.__get_champion_names()

    def __dd_version(self):
        """
        Retrieves the data dragon version for the Data Dragon API
        """
        data = rq.get('https://ddragon.leagueoflegends.com/api/versions.json')
        if data.ok:
            version = data.json()[0]
            setattr(self,'patch_version',version)
            return version

        return False
    

    def __get_champion_names(self):
        url = f'http://ddragon.leagueoflegends.com/cdn/{self.patch_version}/data/en_US/champion.json'
        data = rq.get(url)
        if data.ok:
            data = data.json()
            for name,value in data['data'].items():
                self.champion_names[name] = value['key']
                self.champion_ids[int(value['key'])] = name
            return True
        return False
