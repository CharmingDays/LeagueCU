import json
import os
import typing
import asyncio


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
            file = open(f"{fileDir}\\lcu_settings.json")
            self.settings = json.load(file)
            file.close()
            self.color_print(GREEN_COLOR,"Settings loaded successfully")
        except FileNotFoundError:
            #load default settings
            with open(f'{fileDir}\\default_settings.json','r',encoding='utf-8') as settings_file:
                self.settings = json.loads(settings_file.read())
                self.color_print(RED_COLOR,"Settings file not found, used default settings file")
        

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

