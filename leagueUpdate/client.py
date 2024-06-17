import asyncio
import random
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
@lobby.updater(var=settings)
async def on_connect(_:Connection):
    print("Connected to League Client")
    summoner_info = await summoner.summoner_info()
    print(f"Summoner: {summoner_info['displayName']}\nID: {summoner_info['summonerId']}\nLevel: {summoner_info['summonerLevel']}")
    print(await lobby.lobby_settings())


@client.ws.register('/lol-champ-select/v1/session',event_types=('CREATE','UPDATE'))
@champion_select.updater
async def on_champion_select(_:Connection,response:Response):
    if not response.data:
        return
    if await settings['champion_select','automate']:
        # TODO turn delay into seconds remaining before phase ends
        pick_delay = await settings['champion_select','pick_delay']
        ban_delay = await settings['champion_select','ban_delay']
        await champion_select.auto_ban(await settings['champion_select'],delay=ban_delay)
        await champion_select.auto_pick(await settings['champion_select'],delay=pick_delay)



    

@client.ws.register('/lol-matchmaking/v1/ready-check',event_types=('UPDATE',))
async def matchmaking_events(connection:Connection,event:Response):
    # Automatically keep accepting matches when found until script closed
    if event.data['playerResponse'] == "None" and await settings['lobby','auto_accept']:
        delay = await settings['lobby','accept_delay']
        if delay > 0:
            await asyncio.sleep(delay)
        await connection.request("post",'/lol-matchmaking/v1/ready-check/accept')



@client.ws.register('/lol-matchmaking/v1/search',event_types=('UPDATE',))
@lobby.updater()
async def avoid_autofill(connection:Connection,event:Response):
    """Avoid getting filled by restarting queue with 10 second delay if estimated queue time is exceeded

    Args:
        connection (Connection): _description_
        event (Response): _description_
    """
    if event.data['timeInQueue']+15 > event.data['estimatedQueueTime']:
        lobby_info = await lobby.lobby_info()   
        if lobby_info['localMember']['isLeader']:
            await lobby.cancel_queue()
            await asyncio.sleep(10)
            await lobby.find_match()


#TODO honor most damage or friend or random or role
@client.ws.register('/lol-gameflow/v1/gameflow-phase',event_types=("UPDATE",))
async def gameflow_phases(conn:Connection,event:Response):
    # ReadyCheck,ChampSelect,GameStart,InProgress,WaitingForStats,PreEndOfGame,EndOfGame
    print('gameflow:',event.data)
    if event.data == 'PreEndOfGame':
        if await settings['post_game','skip_honor']:
            return await conn.request('post','/lol-honor-v2/v1/honor-player',data={'honorPlayerRequest':False})
        else:
            if not await settings['lobby','party_members']:
                return await conn.request('post','/lol-honor-v2/v1/honor-player',data={'honorPlayerRequest':False})
            ballot_resp = await conn.request('get','/lol-honor-v2/v1/ballot')
            player_data = await ballot_resp.json()
            honor_target = random.choice(await settings['lobby','party_members'])
            for player in player_data['eligiblePlayers']:
                if player['summonerId'] == honor_target:
                    honor_data = {
                        "honorCategory": "GGHeart",
                        "summonerId": honor_target
                        }
                    await conn.request('post','/lol-honor-v2/v1/honor-player',data=honor_data)

    if event.data == 'EndOfGame':
        if await settings['post_game','play_again']:
            await conn.request("post",'/lol-lobby/v2/play-again')


@client.ws.register('/lol-champ-select/v1/session/trades',event_types=('UPDATE',))
async def handle_trades(connection:Connection,event:Response):
    # if settings.settings['champion_select']['accept_trades']:
    #     await champion_select.auto_trade(connection,event.data) 
    pass



client.start()