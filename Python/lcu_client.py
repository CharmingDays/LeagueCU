from typing import Union,List
import os, json,time
from requests import Response
from BaseAPI import (
    Lobby,ChampSelect,Summoner,
    LiveGameData,Matchmaking,PostMatch,
    Runes,Chat
    )

class LCU_Client(Lobby,ChampSelect,Summoner,LiveGameData,Matchmaking,PostMatch,Runes,Chat):
    """
    Docs for LCU can be found here
        https://lcu.vivide.re/
        https://github.com/Remlas/lolcup-tools/blob/master/AllRequests.txt

    """
    def __init__(self):
        super().__init__()

class AutoFunctions(LCU_Client):
    """
    NOTE: This is not recommended to automate the client, you should use the `lcu_driver` and subscribe to the endpoints instead.

    A class that uses the LCU class to implement  automatic functions
    CURRENT FEATURES:
        - auto_accept:
            -- automatically start queue or wait until queue starts and accepts the match for you until in champion select.

        - auto_ban:
            -- automatically ban a champion from a list

        - auto_runes:
            -- automatically set runes if user has a defined runes for the selected champion.
    """
    def __init__(self):
        super().__init__()

    def auto_champion_selection(self,champPicks:List[str],champBan:List[str]) -> Response:
        """
        Automatically select and lock in champion
        -Hover champion
        -ban champion
        -lock in champion

        """
        banAble = self.bannable_champions().json()
        actorId = self.local_player_cell_id
        while not self.game_state:
            if not self.in_champion_select:
                # prevent non scribble error.
                continue
            if self.is_planning_phase and self.local_player_team_data['championPickIntent'] == 0: #TODO: CHECK TO SEE IF USER ALREADY HOVERED CHAMPION
                #NOTE: PICK INTENT PHASE(PLANNING PHASE)
                self.hover_champion(champPicks[0])
            if self.is_banning_phase and self.get_phase_data(actorId,'ban')['completed'] is False:
                #NOTE: BANNING PHASE
                #ban phase, user has not banned
                hoveredChampions = self.hovered_champions()
                for champ in champBan:
                    champId =self.champion_by_name(champ)
                    if champId in banAble and champId not in hoveredChampions:
                        ban = self.ban_champion(champ)
                        if ban.ok:
                            # ban successful
                            break

            if self.is_picking_phase and self.get_phase_data(actorId,'pick')['completed'] is False and self.is_local_player_turn:
                # Checks phase,user's turn, action status(turn completed?)
                #NOTE: PICKING PHASE - USER'S TURN
                for champ in champPicks:
                    localPlayerHover = self.local_player_team_data
                    if localPlayerHover['championPickIntent'] != self.champion_by_name(champ) and localPlayerHover['championPickIntent'] != 0:
                        pick = self.pick_champion(localPlayerHover['championPickIntent'])
                    else:
                        pick = self.pick_champion(champ)
                    if pick.ok:
                        # action successful
                        break
                        
            time.sleep(.1)


    def auto_accept_game(self,picks=None,bans=None) -> Response:
        """
        Auto accept matches until summoner in game.
        #NOTE: DODGE NOT TESTED
        """
        # Not in game yet
        if self.is_room_owner and self.ready_to_start:
            self.find_match()

        while not self.game_state:
            #wait for game to start
            if not self.in_champion_select:
                #waiting to be in champ select
                if self.in_queue:
                    #waiting in queue
                    if self.match_found and self.ready_check().json()['playerResponse'] != "Accepted":
                        #match found and accepted
                        self.accept_match()

            if self.in_champion_select:
                if picks is None or bans is None:
                    continue
                else:
                    self.auto_champion_selection(picks,bans)
            time.sleep(.1)

        return self.game_data

def write_data(func,*args):
    """
    Simple function to write the json contents of the data into my file dir
    """
    if args:
        data= func(*args)   
    else:
        data = func()
    with open("D:\\Developer\\LeagueCU\\test\\{}.json".format(func.__name__),'w',encoding='utf-8') as file:
        if type(data) != dict:
            data = data.json()
        file.write(json.dumps(data))

        


lol = LCU_Client()
lol.create_lobby("RANKED","BOTTOM","MIDDLE")