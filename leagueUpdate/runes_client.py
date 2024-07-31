import asyncio
import os
import typing
from lcu_driver import Connector
from lcu_driver.connection import Connection as Conn
from lcu_driver.events.responses import WebsocketEventResponse as Resp
import yaml



def load_runes() -> typing.Dict[int,typing.Any]:
    path = os.path.dirname(os.path.dirname(__file__))
    file = open(f"{path}/config/runes.yaml")
    data = yaml.load(file,Loader=yaml.FullLoader)
    return data


CustomRunes = load_runes()
client = Connector()
async_event = asyncio.Event()



@client.ready
async def ready(connection:Conn):
    print("Client is ready")



async def champion_is_selected(event):
    data = event.data
    all_actions = data['actions'] 
    cell_id = data['localPlayerCellId']
    for action_list in all_actions:
        for action in action_list:
            if action['actorCellId'] == cell_id and action['type'] == 'pick' and action['completed']:
                return True
    return False

    
async def delete_rune_page(runeId:int) -> None:
    await client.connection.request("delete",f'/lol-perks/v1/pages/{runeId}')

async def create_rune_page(rune_tree:typing.Dict[str,typing.Any]) -> None:
    await client.connection.request("post",'/lol-perks/v1/pages',data=rune_tree)

async def current_rune() -> typing.Dict[str,typing.Any]:
    runes = await client.connection.request("get",'/lol-perks/v1/currentpage')
    return await runes.json()

def player_data(session_data) -> typing.Dict[str, typing.Any]:
    cell_id = session_data['localPlayerCellId']
    teamData = session_data['myTeam']
    for player in teamData:
        if player['cellId'] == cell_id:
            return player
    return None

async def update_rune(session_data):
    async_event.set()
    current = await current_rune()
    selected_champion = player_data(session_data)['championId']
    if current['name'] == CustomRunes[selected_champion]['name']:
        return
    else:
        await delete_rune_page(current['id'])
        await create_rune_page(CustomRunes[selected_champion])


@client.ws.register('/lol-gameflow/v1/gameflow-phase',event_types=('UPDATE','CREATE'))
async def gameflow_phase(_:Conn,event:Resp):
    data = event.data
    if data != "ChampSelect":
        async_event.clear()
    print(data)

@client.ws.register('/lol-champ-select/v1/session',event_types=('UPDATE','CREATE'))
async def auto_runes(_:Conn,event:Resp):
    if await champion_is_selected(event):
        if not async_event.is_set():
            await update_rune(event.data)
        return

client.start()