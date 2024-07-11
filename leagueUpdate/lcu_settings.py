import os
import typing
import asyncio
import requests
import yaml
from utils import include_constructor
   

yaml.add_constructor('!include',include_constructor,yaml.FullLoader)

RED_COLOR = "\033[31m"
GREEN_COLOR = "\033[32m"
RESET_COLOR = "\033[0m"
BLUE_COLOR = "\033[34m"
class LcuSettings(object):
    def __init__(self) -> None:
        self.settings:typing.Dict[str,typing.Any] = {}
        self.lock = asyncio.Lock()
        self.load_settings()

    def color_print(self,color:str,text:str):
        print(f"{color}{text}{RESET_COLOR}")

    def load_settings(self):
        fileDir:str = os.path.dirname(os.path.dirname(__file__))
        try:
            file = open(f"{fileDir}/config/lcu_settings.yaml",'r')
            self.settings = yaml.load(file,Loader=yaml.FullLoader)
            file.close()
            self.color_print(GREEN_COLOR,"Settings loaded successfully")
        except FileNotFoundError:
            #load default settings
            backup_url = 'https://gist.githubusercontent.com/CharmingDays/6e7d673403439b697b10a2d6100e2288/raw/d7f05b2f682da92ab1b3b552c443c3b279e92994/lcu_settings.yaml'
            data = requests.get(backup_url)
            with open(f'{fileDir}/config/lcu_settings.yaml','w') as file:
                file.write(data.text)
                self.settings = yaml.load(data.text,Loader=yaml.FullLoader)
                self.color_print(RED_COLOR,"Settings file not found, used backup from https://gist.github.com/CharmingDays/6e7d673403439b697b10a2d6100e2288#file-lcu_settings-yaml")
        

    async def __getitem__(self,keys:tuple|str ):
        async with self.lock:
            if not isinstance(keys,tuple):
                keys = (keys,)
            value = self.settings
            for key in keys:
                value = value.get(key)
            return value


    async def set(self,keys:tuple|str,value:typing.Any):
        async with self.lock:
            if not isinstance(keys,tuple):
                keys = (keys,)
            previous = self.settings
            for key in keys:
                current = previous.get(key,None)
                if current is None or keys[-1] == key:
                    previous[key] = value
                    return
                previous = current

    def get(self,keys:tuple|str) -> typing.Any:
        if not isinstance(keys,tuple):
            keys = (keys,)
        value = self.settings
        for key in keys:
            value = value.get(key)
        return value

    def add_bans(self,role:str,champion:str):
        self.settings['champion_select'][role]['bans'].append(champion)
    
    def remove_ban(self,role:str,champion:str):
        try:
            self.settings['champion_select'][role]['bans'].remove(champion)
        except ValueError:
            self.color_print(RED_COLOR,f"Could not find {champion} in bans for {role}")
    
    def add_picks(self,role:str,champion:str):
        self.settings['champion_select'][role]['picks'].append(champion)

    def remove_pick(self,role:str,champion:str):
        try:
            self.settings['champion_select'][role]['picks'].remove(champion)
        except ValueError:
            self.color_print(RED_COLOR,f"Could not find {champion} in picks for {role}")
    
    def output_settings(self):
        print(self.settings['champion_select'])
