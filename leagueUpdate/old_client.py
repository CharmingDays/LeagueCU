import asyncio
from collections import deque
import json
import os
import sys
from lcu_driver.connection import Connection as socketConnection
from lcu_driver.events.responses import WebsocketEventResponse as socketResponse
from lcu_driver.connector import Connector
from leagueUpdate.old_champion_select import ChampionSession


client:Connector = Connector()
champ = ChampionSession()
asyncLock = asyncio.Lock()

def session_settings():
    fileDir = os.path.dirname(__file__)
    if 'lcu_settings.json' not in [file.lower() for file in os.listdir(fileDir)]:
        print("No lcuSettings file detected, please create a lcu_settings.json file in the same directory as the script with the required settings then run this script again")
        input("Press enter to exit")
        with open(f"{fileDir}/lcu_settings.json",'w',encoding='utf-8') as file:
            file.write(json.dumps({}))
        sys.exit()
    with open(f"{fileDir}/lcu_settings.json",'r',encoding='utf-8') as file:
        return json.loads(file.read())


lcu_settings = session_settings()

async def summoner_info(connection:socketConnection):
    summoner = await connection.request('get','/lol-summoner/v1/current-summoner')
    if summoner.ok:
        data = await summoner.json()
        print(f"Summoner: {data['displayName']}\nID: {data['summonerId']}\nLevel: {data['summonerLevel']}")
    



@client.ready
async def client_ready(connection:socketConnection):
    await summoner_info(connection)


@client.ws.register('/lol-champ-select/v1/session',event_types=("UPDATE",))
async def champion_select_events(connection:socketConnection,event:socketResponse) -> None:
    if not event.data.get('actions',None):
        print('NO ACTION DATA',list(event.data.keys())[:2])
    elif event.data:
        print('PRESENT DATA',list(event.data.keys())[:2])
    # if not event.data.get('actions',None):
    #     return
    # champ.update_data(connection,event)
    # await champ.auto_pick(laneChamps=lcu_settings['champ_select']['auto_picks'])
    # await champ.auto_ban(champList=lcu_settings['champ_select']['auto_picks'])



@client.ws.register('/lol-matchmaking/v1/ready-check',event_types=('UPDATE',))
async def matchmaking_events(connection:socketConnection,event:socketResponse):
    # Automatically keep accepting matches when found until script closed
    if event.data['playerResponse'] == "None":
        await connection.request("post",'/lol-matchmaking/v1/ready-check/accept')
        

async def sort_ballot(connection:socketConnection):
    uri = '/lol-honor-v2/v1/ballot'
    resp = await connection.request("get",uri)
    



@client.ws.register('/lol-gameflow/v1/gameflow-phase',event_types=("UPDATE",))
async def gameflow_phases(conn:socketConnection,event:socketResponse):
    # ReadyCheck,ChampSelect,GameStart,InProgress,WaitingForStats,PreEndOfGame,EndOfGame
    async with asyncLock:
        if event.data == "ChampSelect":
            lcu_settings['lobby']['auto_start'] = True

        if event.data == 'EndOfGame':
            await conn.request("post",'/lol-lobby/v2/play-again')
        
        if event.data == "PreEndOfGame":
            await sort_ballot(conn)
            

@client.ws.register('/lol-lobby/v2/lobby',event_types=("UPDATE",))
async def lobby_events(conn,event):
    for _ in range(5):
        await asyncio.sleep(1)
        
    async with asyncLock:
        if event.data['canStartActivity'] and lcu_settings['lobby']['auto_start']:
            await conn.request("post",'/lol-lobby/v2/lobby/matchmaking/search')


@client.ws.register('/lol-matchmaking/v1/search',event_types=("DELETE",))
async def queue_cancelled(_,event):
    async with asyncLock:
        if not event.data:
            lcu_settings['lobby']['auto_start'] = False

    lcu_settings


@client.ws.register('/lol-honor-v2/v1/honor-player',event_types=("UPDATE","CREATE"))
async def player_honor(conn,event):
    # NOTE None -> skip?
    print('honor data',event.data)




@client.ws.register("/lol-champ-select/v1/session/trades",event_types=("CREATE","UPDATE"))
async def trade_session(conn,event):
    print(event.data)




client.start()