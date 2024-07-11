import asyncio
import json
import os
import typing
from lcu_driver.connection import Connection
from lcu_driver.events.responses import WebsocketEventResponse as Response
from lcu_settings import LcuSettings

class LcuRunes(object):
    def __init__(self) -> None:
        self.session:Connection
        self.event_data:Response
        self.settings:LcuSettings
 
    def updater(self,lcu_settings=None):
        def decorator(func):
            async def update_wrapper(*args,**kwargs):
                self.session = args[0]
                try:
                    self.event_data = args[1].data
                except IndexError:
                    pass
                if lcu_settings:
                    if hasattr(self,'settings'):
                        self.settings = lcu_settings
                    else:
                        setattr(self,'settings',lcu_settings)
                return await func(*args,**kwargs)
            return update_wrapper
        return decorator


    async def current_runes(self) -> typing.Dict[str,typing.Any]:
        """Get the currently selected runes page

        Returns:
            dict: The currently selected runes page

        """
        runes = await self.session.request("get",'/lol-perks/v1/currentpage')
        return runes
    

    async def select_rune_page(self,runeId:int) -> None|typing.Dict[str,typing.Any]:
        """Equip a rune page/select rune page as current page

        Args:
            runeId (int): The id of the rune page to equip
        
        Returns:
            The response from the request or None if the request was unsuccessful

        """
        await self.session.request("post",'/lol-perks/v1/pages',data={"id":runeId})


    
    async def delete_rune_page(self,runeId:int) -> None:
        """Delete a rune page

        Args:
            runeId (int): The id of the rune page to delete

        """
        await self.session.request("delete",f'/lol-perks/v1/pages/{runeId}')


    async def create_rune_page(self,name:str,primaryStyleId:int,selectedPerkIds:typing.List[int],subStyleId:int,selectedPerkSubStyleId:int) -> None:
        """Create a new rune page

        Args:
            name (str): The name of the rune page
            primaryStyleId (int): The id of the primary rune style
            selectedPerkIds (list): The ids of the selected runes
            subStyleId (int): The id of the secondary rune style
            selectedPerkSubStyleId (int): The id of the selected secondary rune

        """
        data = {
            "name":name,
            "primaryStyleId":primaryStyleId,
            "selectedPerkIds":selectedPerkIds,
            "subStyleId":subStyleId,
            "selectedPerkSubStyleId":selectedPerkSubStyleId
        }
        await self.session.request("post",'/lol-perks/v1/pages',data=data)
