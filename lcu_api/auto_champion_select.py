import json
import os
import sys
from lcu_driver.connection import Connection as socketConnection
from lcu_driver.events.responses import WebsocketEventResponse as socketResponse
from lcu_driver.connector import Connector
from champ_session import ChampionSession
from clicker import ClickCounter

client:Connector = Connector()
champ = ChampionSession()

def session_settings():
    pwd = os.path.dirname(__file__)
    if 'lcu_settings.json' not in [file.lower() for file in os.listdir(pwd)]:
        print("No lcuSettings file detected, please create a lcu_settings.json file in the same directory as the script with the required settings then run this script again")
        input("Press enter to exit")
        sys.exit()
    with open(f"{pwd}/lcu_settings.json",'r',encoding='utf-8') as file:
        return json.loads(file.read())


lcuSettings = session_settings()

async def summoner_inf(connection:socketConnection):
    summoner = await connection.request('get','/lol-summoner/v1/current-summoner')
    if summoner.ok:
        data = await summoner.json()
        print(f"Summoner: {data['displayName']}\nID: {data['summonerId']}\nLevel: {data['summonerLevel']}")
    



@client.ready
async def client_ready(connection:socketConnection):
    await summoner_inf(connection)



def player_turn(data):
    for actionTypes in data['actions']:
        for action in actionTypes:
            if data['timers']['phase'] == "BAN_PICK" and  action['actorCellId'] == data['localPlayerCellId'] and not action['completed'] and action['isInProgress']:
                return action


async def auto_champ_select(connection:socketConnection,event:socketResponse):
    if player_turn(event.data):
        pass
    

# @client.ws.register('/lol-champ-select/v1/session',event_types=("UPDATE",))
async def champion_select(connection:socketConnection,event:socketResponse) -> None:
    champ.update_data(connection,event)
    if champ.event_phase == "GAME_STARTING":
        # client.stop()
        # start_click_counter()
        return 
    await champ.auto_pick(laneChamps=lcuSettings['champ_select']['auto_picks'])
    await champ.auto_ban(champList=lcuSettings['champ_select']['auto_bans'])





# @client.ws.register('/lol-matchmaking/v1/ready-check',event_types=('UPDATE',))
async def auto_accept_match(connection:socketConnection,event:socketResponse):
    # Automatically keep accepting matches when found until script closed
    if event.data['playerResponse'] == "None":
        await connection.request("post",'/lol-matchmaking/v1/ready-check/accept')
        

# ReadyCheck
# ChampSelect
# GameStart
# InProgress
# WaitingForStats
# PreEndOfGame
# EndOfGame

@client.ws.register('/lol-gameflow/v1/gameflow-phase',event_types=("UPDATE",))
async def post_game(conn:socketConnection,event:socketResponse):
    print(event.data)
    if event.data == "Lobby":
        lcuSettings['clicker_client'] = ClickCounter()
        lcuSettings['click_counter'] = multiprocessing.Process(target=lcuSettings['clicker_client'].start_counter)
    if event.data == "None":
        lcuSettings['clicker_client'].reset_states()
        lcuSettings['click_counter'].terminate()
        

@client.ws.register('/lol-honor-v2/v1/honor-player',event_types=("UPDATE","CREATE"))
async def player_honor(conn,event):
    # NOTE None -> skip?
    event.data


client.start()