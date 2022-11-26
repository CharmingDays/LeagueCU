import json
from lcu_driver import Connector as connector
import os


Connector = connector()

class AutoRunes(object):
    def __init__(self) -> None:
        pass

    
    def setRunePath(self):
        location = os.environ["USERPROFILE"] + "\\Desktop\\"
        with open(location,'w+',encoding='utf-8')as file:
            setattr(self,'data',json.dumps(file))

    async def setRunes(self,champion,connection):
        pass


    async def currentRuneName(self,connection) -> int:
        # returns the current rune and which champion it's for
        pass



clientAPI = AutoRunes()
@Connector.ws.register('/lol-champ-select/v1/session',event_types=('UPDATE',))
async def runes(connection,event):
    champion = event.data['myTeam'][event.data['localPlayerCellId']]['championId']
    currentRune= currentRune(connection)
    if champion != 0:
        return await clientAPI.setRunes(champion,connection)
    if currentRune != champion:
        await clientAPI.setRunes(champion,connection)


Connector.start();
