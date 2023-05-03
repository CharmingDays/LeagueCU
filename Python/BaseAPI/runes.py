from .riotfiles import RiotFiles
from requests import Response
from typing import Union
import json,os
class Runes(RiotFiles):
    def __init__(self) -> None:
        super().__init__()


    def __summoner_info(self) -> Union[dict,bool]:
        url = self.url+'/lol-summoner/v1/current-summoner'
        data = self.session.get(url)

        if data.ok:
            return data.json()
        return False


    def get_rune_list(self) -> Union[dict,bool]:
        summoner = self.__summoner_info()
        if summoner:
            summonerId = summoner['summonerId']
            url = f"/lol-perks/v1/pages"
            data = self.session.get(self.url+url)
            if data.ok:
                return data.json()

        return False

    def get_rune(self,runeId):
        url = self.url+f'/lol-perks/v1/pages/{runeId}'
        data= self.session.get(url)
        if data.ok:
            return data.json()

        return False

    def delete_rune(self,id):
        url = self.url+f'/lol-perks/v1/pages/{id}'
        data= self.session.delete(url)
        if data.ok:
            return data.text
        return False


    def export_runes(self,path=None,fileName='runes'):
        if path is None:
            path = os.getcwd()
        with open(f"{path}\{fileName}.json",'w+',encoding='utf-8') as file:
            fileData = file.read()
            rune_list = self.get_rune_list()
            path = os.getcwd()
            print(path)
            if fileData:
                data = json.dumps(fileData)
                for rune in rune_list['data']:
                    if rune['name'] not in data:
                        data.append(rune)
            else:
                data = rune_list
            
            file.write(str(json.dumps(data)))
            
    def current_rune(self):
        data = self.get_rune_list()
        if data:
            for rune in data:
                if rune['current']:
                    return rune
        return False

    def save_rune(self,path):
        if not os.path.exists(path):
            # create file since it' doesn't exist
            path = os.chdir(os.getcwd())
            file = open(path,'x')
            currentRune = self.current_rune()
            file.write(str(json.dumps(currentRune)))
            file.close() 
            return
        else:
            file = open(path,'r')
            data = json.loads(file.read())
            file.close()
            print(type(data))
            wFile = open(path,'w',encoding='utf-8')
            currentRune = self.current_rune()
            new = True
            for rune in data:
                if rune['name'] == currentRune['name']:
                    new = False
            if new:
                data.append(currentRune)
            
            wFile.write(str(json.dumps(data)))
            return


    def update_rune(self,id,champion,runeTree):
        currentRune = self.get_rune(id)
        currentRune['name'] = f'Local: {champion.lower().title()}'
        primaryStyleId = 8200
        subStyleId =8300
        currentRune['subStyleId'] = subStyleId
        currentRune['primaryStyleId'] = primaryStyleId
        selectedPerkIds = [8214,8226,8210,8237,8345,8347,5008,5008,5002]
        currentRune['selectedPerkIds'] = selectedPerkIds
        url = self.url+f'/lol-perks/v1/pages'
        self.delete_rune(id)
        data = self.session.post(url,data=json.dumps(currentRune))
        return data.json


