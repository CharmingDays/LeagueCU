import WebSocket from 'ws';
import fetch from 'node-fetch';
import { existsSync,readFileSync,watch,writeFileSync} from 'fs';
import https from 'https';



interface LockfileStruct {
    username:string
    address:string
    port:number
    password:string
    token:string
    method:string
    agent:https.Agent
};

class SocketClient {
    agent:https.Agent = new https.Agent({
        rejectUnauthorized:false
    })
    LOCKFILE:any = {}
    socket:WebSocket= new WebSocket('');
    getFile() {
        const path ="C:/Riot Games/League of Legends/lockfile"
        const file = readFileSync(path,'utf-8')
        let data = file.split(":")
        const lockfileData = {
            username : data[0],
            address : '127.0.0.1',
            port : data[2],
            password : data[3],
            token : Buffer.from(`riot:${data[3]}`).toString('base64'),
            method :data[4],
            agent:this.agent
        }
        this.LOCKFILE = lockfileData;
        return lockfileData
    }
    connectSocket() {
        this.socket = new WebSocket(this.LOCKFILE.address)
    }
    start() {
        const path = "C:/Riot Games/League of Legends"
        watch(path,(eventType,filename)=>{
            if (existsSync(`${path}/lockfile`)) {
                this.getFile()
            }
            if (filename == 'lockfile' && eventType == 'rename') {
                if (existsSync(`${path}/lockfile`)) {

                }
                else {

                }
            }
        }) 
    }
}