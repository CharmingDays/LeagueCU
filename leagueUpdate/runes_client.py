from lcu_driver import Connector
from lcu_driver.connection import Connection as Conn
from lcu_driver.events.responses import WebsocketEventResponse as Resp
from runes import LcuRunes
from champion_session import LcuChampionSelectSession

rune_client = LcuRunes()
client = Connector()
champion_select = LcuChampionSelectSession()


@client.ws.register
async def ready(_):
    print("Client is ready")


@champion_select.updater()
@client.ws.register('/lol-champ-select/v1/session',event_types=('UPDATE','CREATE'))
async def champion_select(connection:Conn,event:Resp):
    pass