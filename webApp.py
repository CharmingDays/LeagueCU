import os
import flask
from flask import request
import json
from flask import render_template
import threading
from lcu_driver import Connector
from lcu_driver.connector import Connection
from lcu_driver.events.responses import WebsocketEventResponse as EventResponse
import requests as rq
import typing




class Utils(object):
    def __init__(self) -> None:
        pass


    async def current_rune(self,connection:Connection) -> typing.Dict:
        uri = '/lol-perks/v1/currentpage'
        response = await connection.request('get',uri)
        return await response.json()

    async def delete_current_rune(self,connection:Connection) -> int:
        currentRune = await self.current_rune(connection)
        uri = f'/lol-perks/v1/pages/{currentRune["id"]}'
        response = await connection.request('delete',uri)
        return response.status


    async def change_rune(self,rune,connection:Connection) -> int:
        deleteResponse = await self.delete_current_rune(connection)
        uri = '/lol-perks/v1/pages'
        if deleteResponse:
            response = await connection.request('post',uri,data=json.dumps(rune))
            return response.status
        
    async def accept_match(self,connection:Connection) -> int:
        response = await connection.request("post",'/lol-matchmaking/v1/ready-check/accept')
        return response.status


    async def skip_honor(self,connection:Connection):
        uri =''
        response = await connection.request('post',uri)
        return response.status


    async def play_again(self,connection:Connection) ->int:
        uri = '/lol-lobby/v2/play-again'
        response = await connection.request('post',uri)
        return response.status



app = flask.Flask(__name__)
client = Connector()
utils = Utils()




def setFilePath():
    path = os.path.dirname(__file__)
    os.chdir(path)
setFilePath()

def get_runes():
    RunesUrl = 'https://gist.githubusercontent.com/CharmingDays/093604bbb4822b0333d5fb78e2a91384/raw/7f7f2b30e2c3f72dd09876ab2b21268845962460/season2022.json'
    response = rq.get(RunesUrl)
    return response.json()

SeasonRunes = get_runes()

def currentOptions():
    if os.path.exists(f"userLcuSettings.json"):
        with open(f"userLcuSettings.json",'r',encoding='utf-8') as file:
            return json.loads(file.read())
    else:
        # create the file with default options
        options = {'match':'','runes':'','play_again':''}
        with open(f'userLcuSettings.json','w',encoding='utf-8') as file:
            file.write(json.dumps(options))
            return options

userSettings  = currentOptions()


@app.route('/',methods=['GET'])
def mainPage():
    options = currentOptions()
    return render_template('index.html',**options)



def _update_settings(data):
    newData = {}
    with open(f'userLcuSettings.json','r',encoding='utf-8') as file:
        for key,value in data.items():
            # jsonData[key]= value
            userSettings[key] = value
        newData = userSettings
    open(f"userLcuSettings.json",'w').close()
    file = open(f"userLcuSettings.json",'w',encoding='utf-8')
    file.write(json.dumps(newData))
    return

@app.route('/updateLcuSettings/<data>',methods=["POST"])
def settings_watcher(data):
    _update_settings(json.loads(data))
    return "Settings Updated"


@app.route('/settings',methods=['GET'])
def return_settings():
    return json.dumps(userSettings)



@client.ready
async def client_ready(connection:Connection):
    response = await connection.request("get",'/lol-summoner/v1/current-summoner')
    summoner = await response.json()
    print(f"{summoner['id']}\n{summoner['displayName']}\n{summoner['level']}")



@client.ws.register('/lol-matchmaking/v1/ready-check',event_types=('UPDATE',))
async def auto_accept_match(connection,event):
    # Automatically accept matches when found until script closed
    if userSettings['match'] == 'checked':
        if event.data['playerResponse'] == "None":
            await utils.accept_match(connection)
            print("Match found!!")


@client.ws.register('/lol-champ-select/v1/session',event_types=('UPDATE',))
async def auto_runes(connection:Connection,event:EventResponse):
    print(event.data)
    if userSettings['runes'] == 'checked':
        championId = event.data['myTeam'][event.data['localPlayerCellId']]['championId']
        if championId != 0:
            championRune = SeasonRunes[str(championId)]
            await utils.change_rune(championRune,connection)



@client.ws.register('/',event_types=('UPDATE',))
async def auto_play_again(connection:Connection,event:EventResponse):
    if userSettings['play_again'] == "checked":
        await utils.play_again(connection)

if __name__ == "__main__":
    flaskApp = threading.Thread(target=app.run)
    lcuApp = threading.Thread(target=client.start)
    lcuApp.start()
    flaskApp.start()