import asyncio
from lcu_driver import Connector
from lcu_driver.connection import Connection
from lcu_driver.events.responses import WebsocketEventResponse as Response
from champion_session import LcuChampionSelectSession
from summoner import LcuSummoner
from lcu_settings import LcuSettings
from lobby import LcuLobby
import utils
import time




client:Connector = Connector()
champion_select:LcuChampionSelectSession = LcuChampionSelectSession()
summoner:LcuSummoner = LcuSummoner()
settings:LcuSettings = LcuSettings()
lobby:LcuLobby = LcuLobby()





@client.ready
@summoner.updater
@lobby.updater(settings)
async def on_connect(conn:Connection):
    print("Connected to League Client")
    summoner_info = await summoner.summoner_info()
    if summoner_info.get('errorCode',None):
        await asyncio.sleep(5)
        summoner_info=await summoner.summoner_info()
    print(f"Summoner: {summoner_info['displayName']}\nID: {summoner_info['summonerId']}\nLevel: {summoner_info['summonerLevel']}")
    print(await lobby.lobby_settings())



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
    if await settings['lobby','avoid_autofill']:
        lobby_info = await lobby.lobby_info() 
        if lobby_info['localMember']['isLeader']:
            if event.data['timeInQueue']+30 > event.data['estimatedQueueTime']:
                await lobby.cancel_queue()
                await asyncio.sleep(10)
                await lobby.find_match()

@client.ws.register('/lol-gameflow/v1/gameflow-phase',event_types=("UPDATE",))
async def gameflow_phases(conn:Connection,event:Response):
    # Matchmaking,ReadyCheck,ChampSelect,GameStart,InProgress,WaitingForStats,PreEndOfGame,EndOfGame, Lobby
    print('gameflow:',event.data)

    if event.data == 'Matchmaking':
        lobby_data = await lobby.lobby_info()
        local_player_id = lobby_data['localMember']['summonerId']
        if len(lobby_data['members']) > 1:
            teammate = lobby_data['members'][0]['summonerId'] if lobby_data['members'][0]['summonerId'] != local_player_id else lobby_data['members'][1]['summonerId']
            await settings.set(('lobby','teammate'),teammate)
        else:
            await settings.set(('lobby','teammate'),"")
    if event.data == "ChampSelect":
        honoring_user = await settings['post_game','honor_teammate']
        print("Honor teammate:",honoring_user)
            
    # if event.data == 'GameStart':
    #     settings.settings['lobby'].remove('stopped',None)# reset avoid autofill counter
    if event.data == 'PreEndOfGame':
        skip_delay = settings.get(('post_game','skip_honor_delay'))
        if not await settings['post_game','honor_teammate'] or await settings['lobby','teammate'] == None:
            if skip_delay > 0:
                await asyncio.sleep(skip_delay)
            return await client.connection.request('post','/lol-honor-v2/v1/honor-player',data={'honorPlayerRequest':False})

        else:
            # ballot_resp = await conn.request('get','/lol-honor-v2/v1/ballot')
            # player_data = await ballot_resp.json()
            # print(player_data)
            # await conn.request('post','/lol-honor-v2/v1/honor-player',data={'honorPlayerRequest':False})
            honor_data = {
                "honorCategory": settings.get(('post_game','honor_types','heart')),
                "summonerId": await settings['lobby','teammate'],
                "honorPlayerRequest": True
                }
            await asyncio.sleep(6)
            print("Honoring:",honor_data)
            await client.connection.request('post','/lol-honor-v2/v1/honor-player',data=honor_data)

    if event.data == 'EndOfGame':
        if await settings['post_game','play_again']:
            if await settings['post_game','play_again_delay'] > 0:
                await asyncio.sleep(await settings['post_game','play_again_delay'])
            await conn.request("post",'/lol-lobby/v2/play-again')


if __name__ == "__main__":
    client.start()
