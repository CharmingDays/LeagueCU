from lcu_driver.events.responses import WebsocketEventResponse as SocketResponse
from aiohttp.client_reqrep import ClientResponse
from lcu_driver.connection import Connection


class Utils(object):
    def __init__(self) -> None:
        pass

    async def current_summoner(self,connection:Connection):
        uri = '/lol-summoner/v1/current-summoner'
        response = await connection.request('get',uri)
        return await response.json()

    async def current_rune(self,connection:Connection) -> ClientResponse:
        uri = '/lol-perks/v1/currentpage'
        response = await connection.request('get',uri)
        return response

    async def delete_current_rune(self,connection:Connection) ->ClientResponse:
        currentRune = await self.current_rune(connection)
        uri = f'/lol-perks/v1/pages/{currentRune["id"]}'
        response = await connection.request('delete',uri)
        return response

    async def all_runes(self,connection:Connection):
        uri = '/lol-perks/v1/pages'
        response = await connection.request('get',uri)
        return response


    async def delete_rune(self,connection:Connection,runeId):
        uri = f'/lol-perks/v1/pages/{runeId}'
        response = await connection.request('delete',uri)
        return response

    async def create_rune(self,connection:Connection,rune):
        uri = '/lol-perks/v1/pages'
        response = await connection.request("post",uri,data=rune)
        return response 


    async def accept_match(self,connection:Connection) -> int:
        response = await connection.request("post",'/lol-matchmaking/v1/ready-check/accept')
        return response.status


    async def skip_honor(self,connection:Connection):
        uri =''
        response = await connection.request('post',uri)
        return response.status


    async def play_again(self,connection:Connection) ->int:
        uri = '/lol-lobby/v2/play-again'
        response = await connection.request('post',uri)
        return response.status
