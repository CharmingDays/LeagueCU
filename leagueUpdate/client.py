import asyncio
from lcu_driver import Connector
from lcu_driver.connection import Connection
from lcu_driver.events.responses import WebsocketEventResponse as Response
from champion_session import LcuChampionSelectSession
from summoner import LcuSummoner
from lcu_settings import LcuSettings
from lobby import LcuLobby
import utils
from game_phases import GameFlowPhase



gameflow=GameFlowPhase()
client:Connector = Connector()
champion_select:LcuChampionSelectSession = LcuChampionSelectSession()
summoner:LcuSummoner = LcuSummoner()
settings:LcuSettings = LcuSettings()
lobby:LcuLobby = LcuLobby()



@client.ready
@summoner.updater
async def on_connect(_: Connection):
    print("Waiting for League Client connection...")
    summoner_info = await summoner.summoner_info()
    while summoner_info.get('errorCode'):
        await asyncio.sleep(5)
        summoner_info = await summoner.summoner_info()
    
    print(f"Summoner: {summoner_info['displayName']}\nID: {summoner_info['summonerId']}\nLevel: {summoner_info['summonerLevel']}")



@client.ws.register('/lol-champ-select/v1/session',event_types=('CREATE','UPDATE'))
@champion_select.updater(settings)
async def on_champion_select(_:Connection,response:Response):
    if not response.data:
        return
    if await settings['champion_select','automate']:
        await champion_select.ban_and_pick()



@client.ws.register('/lol-matchmaking/v1/ready-check',event_types=('UPDATE',))
async def matchmaking_events(connection:Connection,event:Response):
    # Automatically keep accepting matches when found until script closed
    if event.data['playerResponse'] == "None" and settings.get(('lobby','auto_accept')):
        delay = await settings['lobby','accept_delay']
        if delay > 0:
            await utils.wait_until(10*1000,delay)
        await connection.request("post",'/lol-matchmaking/v1/ready-check/accept')




@client.ws.register('/lol-matchmaking/v1/search',event_types=('UPDATE',))
@lobby.updater()
async def avoid_autofill(connection:Connection,event:Response):
    """Avoid getting filled by restarting queue with 10 second delay if estimated queue time is exceeded

    Args:
        connection (Connection): The aiohttp connection object
        event (Response): _description_
    """
    if event.data['readyCheck']['timer'] > 0:
        # pause if there is a dodge timer
        return
    excess_time = await settings['lobby','excess_queue_time']
    if await settings['lobby','avoid_autofill']:
        lobby_info = await lobby.lobby_info() 
        if lobby_info['localMember']['isLeader'] and len(lobby_info['members']) == 1:
            if event.data['timeInQueue']+excess_time > event.data['estimatedQueueTime']:
                await lobby.cancel_queue()
                await asyncio.sleep(10)
                await lobby.find_match()



@client.ws.register('/lol-gameflow/v1/gameflow-phase',event_types=("UPDATE",))
@gameflow.updater(settings)
async def gameflow_phases(conn:Connection,event:Response):
    # Matchmaking,ReadyCheck,ChampSelect,GameStart,InProgress,WaitingForStats,PreEndOfGame,EndOfGame, Lobby
    print('gameflow:',event.data)
    await gameflow.match_gameflow(event.data)



if __name__ == "__main__":
    client.start()