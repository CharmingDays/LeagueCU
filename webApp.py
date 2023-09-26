import os
import flask
from flask import request
import json
from flask import render_template
import threading
from lcu_driver import Connector
from lcu_driver.connector import Connection
from lcu_driver.events.responses import WebsocketEventResponse as EventResponse
import multiprocessing



app = flask.Flask(__name__)
client = Connector()


def setFilePath():
    path = os.path.dirname(__file__)
    os.chdir(path)
setFilePath()



userSettings = {
    'match':'',
    'runes':''
}


def currentOptions():
    if os.path.exists(f"userLcuSettings.json"):
        with open(f"userLcuSettings.json",'r',encoding='utf-8') as file:
            return json.loads(file.read())
    else:
        # create the file with default options
        options = {'match':'','runes':''}
        with open(f'userLcuSettings.json','w',encoding='utf-8') as file:
            file.write(json.dumps(options))
            return options

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
async def client_ready(con):
    print("LCU Ready!")


@client.ws.register('/lol-matchmaking/v1/ready-check',event_types=('UPDATE',))
async def auto_accept_match(connection,event):
    # Automatically accept matches when found until script closed
    if userSettings['match'] == 'checked':
        if event.data['playerResponse'] == "None":
            await connection.request("post",'/lol-matchmaking/v1/ready-check/accept')
            print("Match found!!")


@client.ws.register('/lol-champ-select/v1/session',event_types=('UPDATE',))
async def auto_runes(connection:Connection,event:EventResponse):
    pass




# if __name__ == "__main__":
flaskApp = threading.Thread(target=app.run)
lcuApp = threading.Thread(target=client.start)
lcuApp.start()
flaskApp.start()