import json
from lcu_driver import Connector
import time
from BaseAPI import Runes,ChampSelect
connector = Connector()



Rune = Runes()
select = ChampSelect()
path = r"C:\Users\kowai\Desktop\customRunes.json"
@connector.ready
async def connect(connection):
    print('LCU API is ready to be used.')


@connector.ws.register('/lol-champ-select/v1/session',event_types=('UPDATE',))
async def champ_rune(connection,event):
    championId = event.dat['myTeam'][event.data['localPlayerCellId']]['championId']
    currentRune = Rune.current_rune()
    championName = currentRune['name'].replace('Love Maker:',Rune.champion_ids[championId])
    file = open(path,'r',encoding='utf-8')
    runes = json.loads(file)
    for rune in runes:
        if championName in rune['name'].lower():
            pass
    
    


@connector.ws.register('/lol-summoner/v1/current-summoner', event_types=('UPDATE',))
async def icon_changed(connection, event):
    print(f'The summoner {event.data["displayName"]} was updated.')



connector.start()