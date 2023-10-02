import os
import flask
import json
from flask import render_template
import threading
from lcu_driver import Connector
from lcu_driver.connector import Connection





app = flask.Flask(__name__)
client = Connector()
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
async def auto_accept_match(connection:Connection,event):
    # Automatically accept matches when found until script closed
    if userSettings['match'] == 'checked':
        if event.data['playerResponse'] == "None":
            await connection.request('post','/lol-matchmaking/v1/ready-check/accept')
            print("Match found!!")

if __name__ == "__main__":
    flaskApp = threading.Thread(target=app.run)
    lcuApp = threading.Thread(target=client.start)
    lcuApp.start()
    flaskApp.start()