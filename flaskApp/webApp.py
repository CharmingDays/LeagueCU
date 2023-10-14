import os
import time
import flask
import json
from flask import render_template
import threading
from lcu_driver import Connector
from lcu_driver.connector import Connection
from lcu_driver.events.responses import WebsocketEventResponse as EventResponse
from baseAPI.champion_select import ChampSelect
from dotenv import load_dotenv
import logging
load_dotenv()
logging.basicConfig(filename='lcu.log',filemode='w',format='%(name)s - %(message)s',level=logging.INFO)

app = flask.Flask(__name__)
client = Connector()
lcu_session = {
    'champion_select':{
        'instance':ChampSelect()
    }
}
lcu_session['champion_select']['instance']()

DESKTOP = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')

def currentOptions():
    if os.path.exists(f"{DESKTOP}\\userLcuSettings.json"):
        with open(f"{DESKTOP}\\userLcuSettings.json",'r',encoding='utf-8') as file:
            return json.loads(file.read())
    else:
        # create the file with default options
        options = {'match':'','runes':'','play_again':''}
        with open(f'{DESKTOP}\\userLcuSettings.json','w',encoding='utf-8') as file:
            file.write(json.dumps(options))
            return options

userSettings  = currentOptions()


@app.route('/',methods=['GET'])
def mainPage():
    options = currentOptions()
    return render_template('index.html',**options)



def _update_settings(data):
    newData = {}
    with open(f'{DESKTOP}\\userLcuSettings.json','r',encoding='utf-8') as _:
        for key,value in data.items():
            # jsonData[key]= value
            userSettings[key] = value
        newData = userSettings
    open(f"{DESKTOP}\\userLcuSettings.json",'w').close()
    file = open(f"{DESKTOP}\\userLcuSettings.json",'w',encoding='utf-8')
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
async def auto_accept_match(connection:Connection,event:EventResponse):
    # Automatically accept matches when found until script closed
    if userSettings['match'] == 'checked':
        if event.data['playerResponse'] == "None":
            return await connection.request('post','/lol-matchmaking/v1/ready-check/accept')


@client.ws.register('/lol-champ-select/v1/session',event_types=("UPDATE",))
async def champion_select_session(conn:Connection,event:EventResponse):
    localSession:ChampSelect = lcu_session['champion_select']['instance']
    localSession.updateData(conn,event)
    cellId = event.data['localPlayerCellId']
    playerData = event.data['myTeam'][cellId]
    pickIntent = event.data['myTeam'][cellId]['championPickIntent']
    logging.info(playerData,time.time())
    if (localSession.is_planning_phase and pickIntent == 0) or pickIntent == 0:
        await localSession.hover_champion('varus')
        logging.info("Selected varus")
    if localSession.is_local_player_turn:
        if localSession.is_banning_phase:
            await localSession.ban_champion('blitzcrank')

        if localSession.is_picking_phase:
            await localSession.pick_champion('varus')



if __name__ == "__main__":
    flaskApp = threading.Thread(target=app.run)
    lcuApp = threading.Thread(target=client.start)
    lcuApp.start()
    flaskApp.start()
