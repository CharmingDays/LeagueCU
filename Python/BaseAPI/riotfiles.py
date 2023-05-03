import base64
import os
import requests as rq
import json
class RiotFiles(object):
    """
    Class for dealing with riotgames' files and other external files for LCU
        - lockfile: the file containing the port, login, http method
        - riotgames.pem: the file containing the SSL certification for making the https requests
    """
    def __init__(self) -> None:
        self.session = rq.Session()
        self.lockfile()
        self.riotgames_SSL()
        self.session.headers = {'Authorization':f"Basic {self.token}",'Accept': 'application/json'}
        self.champion_ids = {}
        self.champion_names = {}
        self._dd_version()
        self.get_champion_names()

    def _dd_version(self):
        """
        Retrieves the data dragon version for the Data Dragon API
        """
        data = rq.get('https://ddragon.leagueoflegends.com/api/versions.json')
        if data.ok:
            version = data.json()[0]
            setattr(self,'patch_version',version)
            return version

        return False
    

    def get_champion_names(self):
        url = f'http://ddragon.leagueoflegends.com/cdn/{self.patch_version}/data/en_US/champion.json'
        data = rq.get(url)
        if data.ok:
            data = data.json()
            for name,value in data['data'].items():
                self.champion_names[name] = value['key']
                self.champion_ids[int(value['key'])] = name
            return True
        return False

    def lockfile(self,filePath:str=None):
        """
        Look for the lockfile and setup token and url from lockfile.
        NOTE: THE CLASS WON'T BE ABLE TO MAKE REQUESTS WITHOUT THE LOCKFILE SETUP
        """
        defaultLockfile = r'C:\Riot Games\League of Legends\lockfile'
        if filePath:
            # set the filePath param to value of defaultLockfile if argument for filePath not given
            defaultLockfile = filePath

        if not os.path.exists(defaultLockfile):
            # lock file doesn't exist in default defaultLockfile path
            raise FileExistsError("lockfile not found, please run and login the lol client.")
        else:
            defaultLockfile = open(defaultLockfile,'r')
        rawData = defaultLockfile.read()
        defaultLockfile.close()
        rawData = rawData.split(":") # convert to list
        data = {"port":rawData[2],"auth":rawData[3],"method":rawData[4]+"://127.0.0.1"} #turn into dict
        token = base64.b64encode(f'riot:{data["auth"]}'.encode()).decode()
        url = f"{data['method']}:{data['port']}"
        # set class attributes
        setattr(self,'token',token)
        setattr(self,'url',url)


    def riotgames_SSL(self):
        """
        sets the root certificate for the requests
        Downloads and creates one if it doesn't exist in current working dir
        """
        current_dir = os.getcwd()
        if 'riotgames.pem' not in os.listdir():
            #retrieve the SSL cert from github gist
            cert = self.session.get('https://gist.githubusercontent.com/CharmingDays/6e7d673403439b697b10a2d6100e2288/raw/ff15e0765da4a4d71b73b673cffb20e7d5461a64/riotgames.pem')
            with open('riotgames.pem','w',encoding='utf-8') as pemFile:
                pemFile.write(cert.text)
                pemFile.close()
            self.session.verify = r"{}\riotgames.pem".format(current_dir)

        else:
            self.session.verify = r"{}\riotgames.pem".format(current_dir)

