from lcu_driver import Connector
import time
connector = Connector()


@connector.ready
async def connect(connection):
    print('LCU API is ready to be used.')




@connector.ws.register('/lol-champ-select/v1/session',event_types=('UPDATE',))
async def champ_rune(connection,event):
    print(event.data,time.time())

@connector.ws.register('/lol-summoner/v1/current-summoner', event_types=('UPDATE',))
async def icon_changed(connection, event):
    print(f'The summoner {event.data["displayName"]} was updated.')




connector.start()