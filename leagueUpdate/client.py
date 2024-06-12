import asyncio
from lcu_driver import Connector
from lcu_driver.connection import Connection
from lcu_driver.events.responses import WebsocketEventResponse as Response
from champion_session import LcuChampionSelectSession
from summoner import LcuSummoner
from lcu_settings import LcuSettings
from lobby import LcuLobby





client:Connector = Connector()
champion_select:LcuChampionSelectSession = LcuChampionSelectSession()
summoner:LcuSummoner = LcuSummoner()
settings:LcuSettings = LcuSettings()
lobby:LcuLobby = LcuLobby()







@client.ready
@summoner.updater
async def on_connect(_:Connection):
    print("Connected to League Client")
    summoner_info = await summoner.summoner_info()
    print(f"Summoner: {summoner_info['displayName']}\nID: {summoner_info['summonerId']}\nLevel: {summoner_info['summonerLevel']}")




@client.ws.register('/lol-champ-select/v1/session',event_types=('CREATE','UPDATE'))
@champion_select.updater
async def on_champion_select(_:Connection,response:Response):
    if not response.data:
        return
    if settings.settings['champion_select']['automate']:
        await champion_select.auto_ban(settings.settings['champion_select'])
        await champion_select.auto_pick(settings.settings['champion_select'])




@client.ws.register('/lol-matchmaking/v1/ready-check',event_types=('UPDATE',))
async def matchmaking_events(connection:Connection,event:Response):
    # Automatically keep accepting matches when found until script closed
    if event.data['playerResponse'] == "None" and settings.settings['lobby']['auto_accept']:
        await connection.request("post",'/lol-matchmaking/v1/ready-check/accept')



@client.ws.register('/lol-matchmaking/v1/search',event_types=('UPDATE',))
@lobby.updater
async def avoid_autofill(connection:Connection,event:Response):
    """Avoid getting filled by restarting queue with 10 second delay if estimated queue time is exceeded

    Args:
        connection (Connection): _description_
        event (Response): _description_
    """
    if event.data['timeInQueue']+15 > event.data['estimatedQueueTime']:
        lobby_info = await lobby.lobby_info()
        if lobby_info['localMember']['isLeader']:
            await connection.request("DELETE",'/lol-lobby/v2/lobby/matchmaking/search')
            await asyncio.sleep(10)
            await client.connection.request("post",'/lol-lobby/v2/lobby/matchmaking/search')



@client.ws.register('/lol-gameflow/v1/gameflow-phase',event_types=("UPDATE",))
async def gameflow_phases(conn:Connection,event:Response):
    # ReadyCheck,ChampSelect,GameStart,InProgress,WaitingForStats,PreEndOfGame,EndOfGame
    if event.data == 'EndOfGame' and settings.settings['post_game']['play_again']:
        await conn.request("post",'/lol-lobby/v2/play-again')
    if event.data == 'PreEndOfGame':
        resp = await conn.request('post','lol-honor-v2/v1/mutual-honor/ack')
        data = await resp.json()
        print(data)
        


client.start()