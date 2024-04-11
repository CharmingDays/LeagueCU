import asyncio
import json
from dotenv import load_dotenv
import mouse
import aiohttp
import typing
import urllib3



load_dotenv()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ClickCounter(object):
    def __init__(self,session:aiohttp.ClientSession):
        self.summonerInfo = {}
        self.playerInfo = {}
        self.clicks = {'left': 0, 'right': 0}
        self.session:aiohttp.ClientSession = session




    async def fetchMatchHistory(self):
        uri = "/lol-match-history/v1/products/lol/current-summoner/matches?begIndex=0&endIndex=2"
        response = await self.session.request('GET',uri)
        return response

    async def localPlayerInfo(self):
        response = await self.session.request (f"{self.url}/lol-summoner/v1/current-summoner")
        jsonData = response.json()
        self.summonerInfo = jsonData
        return self.summonerInfo


    def saveGameInfo(self,gameId,clicks,filePath=None) -> None:
        """Save the amount of clicks counted with game ID

        Args:
            gameId (str): The ID of the game 
            clicks (int): the number of clicks made during the game
            filePath (str, optional): The path of the file to save the into into. Defaults to None.
        """
        
        
        if not filePath:
            filePath = r"D:\Developer\Scripts\python\click_counter.json"
        currentData = open(filePath,'r',encoding='utf-8').read()
        open(filePath,'w').close() # clear file data
        currentData = json.loads(currentData)
        if gameId not in currentData:

            currentData[gameId] = clicks    
        with open(filePath,'w',encoding='utf-8') as file:
            file.write(json.dumps(currentData))
        
    async def reset_states(self):
        resp = await self.fetchMatchHistory()
        data = await resp.json()
        self.saveGameInfo(data['games']['games'][0]['gameId'],self.clicks)
        self.clicks = {'left': 0, 'right': 0}
        mouse.unhook(self.counter)
        
    def counter(self,event:mouse.MoveEvent):
        # print(event)
        if hasattr(event, 'button'):
            if event.button == mouse.RIGHT:
                self.clicks['right'] += .5
            elif event.button == mouse.LEFT:
                self.clicks['left'] += .5
            # print(self.clicks,end='\r')


    def start_counter(self):
        mouse.hook(self.counter)

