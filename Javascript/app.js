import {existsSync,readFileSync} from 'fs'
import {request} from 'https'

class RiotFiles {
    constructor () {
    }
    getRiotGamesPem(path=null) {
        if(!path) path = "C:\\Riot Games\\League of Legends\\riotgames.pem"
        if(!existsSync(path)) return false;
        let pemFile = readFileSync(path).toString();
        return pemFile;
    }
    getLockfile(path=null){
        if(!path) path = "C:\\Riot Games\\League of Legends\\lockfile"
        if(!existsSync(path)) return false;
        let lockfileData = readFileSync(path).toString();
        lockfileData = lockfileData.split(':')
        this.lockfile = {
            client: lockfileData[0],
            port1: lockfileData[1],
            port2: lockfileData[2],
            password: lockfileData[3],
            method: lockfileData[4]
        }
        return this.lockfile;
    }
    sleep(milliseconds) {
        return new Promise(resolve =>setTimeout(resolve,milliseconds))
    }
    async waitForLockfile(timeout=5000,path=null) {
        // NOTE: Use function.then((var) => {console.log(var)})
        if(!path) path = "C:\\Riot Games\\League of Legends\\lockfile"
        while (existsSync(path) == false) {
            if(timeout <=0)break;
            await this.sleep(1000)
            timeout-=1000
        }
        return this.getLockfile(path);
    }
}

class Lobby extends RiotFiles {
    constructor(){
        this.getLockfile();
        this.options = {
            hostname:'https://127.0.0.1',
            port:this.lockfile.port2,
            cert:this.getRiotGamesPem()
        }
    }
    create_lobby(mode='DRAFT') {
        let gameModes = {
            "DRAFT": 400,
            "RANKED":420,
            "RANKED_FLEX":440,
            "ARAM":450,
            "BLIND":430,
            "CUSTOM":"CUSTOM_GAME",
            "PRACTICE":"PRACTICETOOL"
        }
        if(!gameModes.hasOwnProperty(mode)) return "Game mode not found"
        this.options['path']='/lol-lobby/v2/lobby'
        this.options['method'] = 'GET'
        return request(options)
    }
}
