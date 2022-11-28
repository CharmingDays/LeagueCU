import { existsSync } from "fs";
import { chdir } from "process";
import { readFileSync } from "fs";
import { Buffer } from "buffer";

class RiotFiles {
    lockfileData:any = {};
    constructor() {
        this.setRiotgamesDir();
        this.lockfile();
    }
    async sleep(ms:number) {
        return new Promise((resolve) => {
          setTimeout(resolve, ms);
        });
      }
    async waitForLockfile() {
        let fileState:boolean = existsSync('lockfile');
        while (!fileState) {
            await this.sleep(1);
        }
    }

    setRiotgamesDir(dirPath?:string) {
        if (dirPath == undefined){
            chdir('C:\\Riot Games\\League of Legends');
        }
        else {
            chdir(dirPath);
        }
    }

    lockfile() {
        if (!existsSync('lockfile')) {
            return false;
        }
        let lockfile:any = readFileSync('lockfile','utf-8');
        lockfile = lockfile.split(':');
        this.lockfileData.name = lockfile[0];
        this.lockfileData.port = lockfile[2];
        this.lockfileData.password = Buffer.from(`riot:${lockfile[3]}`).toString('base64');
        this.lockfileData.method = lockfile[4];
        this.lockfileData;
    }
}

export default RiotFiles;