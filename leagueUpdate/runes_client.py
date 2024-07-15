import os
import typing
from lcu_driver import Connector
from lcu_driver.connection import Connection as Conn
from lcu_driver.events.responses import WebsocketEventResponse as Resp
import yaml
from runes import LcuRunes
from champion_session import LcuChampionSelectSession




def load_runes() -> typing.Dict[int,typing.Any]:
    path = os.path.dirname(os.path.dirname(__file__))
    file = open(f"{path}/config/runes.yaml")
    data = yaml.load(file,Loader=yaml.FullLoader)
    return data


CustomRunes = load_runes()

rune_client = LcuRunes()
client = Connector()
champion_select:LcuChampionSelectSession = LcuChampionSelectSession()


@client.ws.register
async def ready(_):
    print("Client is ready")


@client.ws.register('/lol-champ-select/v1/session',event_types=('UPDATE','CREATE'))
@champion_select.updater()
async def auto_runes(connection:Conn,event:Resp):
    selected_champion = champion_select.player_data['championId']
    if selected_champion != 0:
        champion_rune = CustomRunes[selected_champion]