import {io,Manager} from 'socket.io-client';
import RiotFiles from './riotFile';


let Riot:any = new RiotFiles();
let token:string = Riot.lockfileData['password']
let port:any = Riot.lockfileData['port']
const socket = io(`ws://127.0.0.1:${port}`, {
    auth: {
        token
    }
});
socket.on('connect',()=> {
    console.log(socket.connected);
})