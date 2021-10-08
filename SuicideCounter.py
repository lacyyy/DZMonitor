from os.path import isdir, join
from PIL import ImageFont
from cv2 import imread

from Visuals import DrawInfoSuicideCounter
import util

def GetCurrentRedeploymentDelay(currentdeploymentcount): # in seconds
    return 10 * currentdeploymentcount
def GetNextRedeploymentDelay(currentdeathcount): # in seconds
    return 10 * (currentdeathcount+1)

class SuicideCounter:
    def __init__(self, folder):
        self.redraw_required = True
        
        self.img_bg = imread(join(folder, "image_background.png"))
        
        self.text_font_size = int(util.parseNumberFromFile(32,
            join(folder, 'text_size_pixels.txt')))
        self.text_font = ImageFont.truetype(join(folder, 'font.ttf'), self.text_font_size)
        
        self.text_pos = util.parseNumberListFromFile([0,0],
            join(folder, 'text_pos_xy.txt'))
        if len(self.text_pos) >= 2:
            self.text_pos = (self.text_pos[0], self.text_pos[1])
        else:
            self.text_pos = (0,0)
        
        self.text_rgba = util.parseNumberListFromFile([255,255,255],
            join(folder, 'text_color_rgb.txt'))
        if len(self.text_rgba) >= 3:
            self.text_rgba = (int(self.text_rgba[0]),int(self.text_rgba[1]),int(self.text_rgba[2]),255)
        else:
            self.text_rgba = (255,255,255,255)
        
        self.draw_info = DrawInfoSuicideCounter()
        self.draw_info.suicide_count = 0
        self.draw_info.image_bg      = self.img_bg
        self.draw_info.font          = self.text_font
        self.draw_info.text_rgba     = self.text_rgba
        self.draw_info.text_pos      = self.text_pos
        
        # 0 = client is not a player in a DZ game
        # 1 = client is player in DZ warmup
        # 2 = client is player in live DZ match
        # 3 = client is player in live DZ match and just died (0 HP)
        # 4 = client is player in live DZ match and waits for respawn, watching his mate
        self.state = 0
        self.client_deployments = 1
        self.client_deaths = 0
        self.teammate_id = None
        self.client_last_death = None
        self.client_last_killcount = 0
        self.watch_out_for_kill_decrease = False
        self.client_suicides = 0
        
    
    def update(self, next_gamestate):
        if next_gamestate is None:
            return
        
        gamestate_time = next_gamestate.receive_time
        game_mode = next_gamestate.get("map","mode")
        map_phase = next_gamestate.get("map","phase")
        client_id = next_gamestate.get("provider","steamid")
        visible_player_id     = next_gamestate.get("player","steamid")
        visible_player_health = next_gamestate.get("player","state","health")
        visible_player_kills  = next_gamestate.get("player","match_stats","kills")
        visible_player_deaths = next_gamestate.get("player","match_stats","deaths")
        
        #print('kills, deaths, suicides: ', self.client_last_killcount, self.client_deaths, self.client_suicides)
        
        # count suicide if kill decreased by 1 within X seconds of client death
        # TODO test suicide right before end of match
        
        is_client_spectating = client_id != visible_player_id
        
        # interesting state transitions
        state_trans_has_client_just_died       = False
        state_trans_has_client_just_redeployed = False
        
        # branches to base state
        if next_gamestate.get("map","mode") != 'survival':
            self.state = 0
        
        # switch statement
        
        # 0: client is not a player in a DZ game
        if self.state == 0:
            if (not is_client_spectating and game_mode == 'survival' and
                    map_phase == 'warmup'):
                self.state = 1
            # Only leave base state through warmup
        # 1: client is player in DZ warmup
        elif self.state == 1:
            if (not is_client_spectating and map_phase == 'live' and
                    visible_player_health > 0):
                self.client_deployments = 1
                self.client_deaths = 0
                self.client_last_killcount = 0
                self.teammate_id = None
                self.client_last_death = None
                self.watch_out_for_kill_decrease = False
                self.state = 2
        # 2: client is player in live DZ match
        elif self.state == 2:
            if not is_client_spectating and visible_player_health == 0:
                self.client_last_death = gamestate_time
                state_trans_has_client_just_died = True
                self.state = 3
        # 3: client is player in live DZ match and just died (0 HP)
        elif self.state == 3:
            # If client just died and then sees himself with health, he's watching his suicide -> game over
            if not is_client_spectating and visible_player_health > 0:
                self.state = 0
            # If we started spectating our alive teammate
            elif (is_client_spectating and visible_player_health > 0 and
                    (self.teammate_id is None or self.teammate_id == visible_player_id)):
                self.teammate_id = visible_player_id
                state_trans_just_started_spectating_mate = True
                self.state = 4
            # We started spectating our teammate or enemy and he just died -> game over
            elif is_client_spectating and visible_player_health == 0:
                self.state = 0
            # We started spectating an enemy -> game is over
            elif (is_client_spectating and self.teammate_id is not None and 
                    self.teammate_id != visible_player_id):
                self.state = 0
        # 4: client is player in live DZ match and waits for respawn, watching his mate
        elif self.state == 4:
            if is_client_spectating and visible_player_health == 0:
                self.state = 0
            # We started spectating an enemy -> game is over
            elif (is_client_spectating and self.teammate_id is not None and 
                    self.teammate_id != visible_player_id):
                self.state = 0
            elif not is_client_spectating:
                state_trans_has_client_just_redeployed = True
                self.state = 2
            # If client spectated longer than his waiting time till respawn -> recognize game over
            elif (is_client_spectating and
                    gamestate_time - self.client_last_death > 2.0 + GetCurrentRedeploymentDelay(self.client_deployments)):
                self.state = 0;
        
        # first, handle important state transition actions
        if state_trans_has_client_just_died: # count deaths
            self.client_deaths += 1
        if state_trans_has_client_just_redeployed: # count redeployments
            self.client_deployments += 1
        
        # if client just died
        if state_trans_has_client_just_died:
            self.watch_out_for_kill_decrease = True
        
        # if kills didn't decrease some time after last client's death -> reset
        if self.watch_out_for_kill_decrease:
            if gamestate_time - self.client_last_death > 0.2: # max observed kill decrease delay: 0.077s
                #print("[Suicide Counter] kill decrease check timeout")
                self.watch_out_for_kill_decrease = False
        
        # check if kills decreased after last client's death
        if self.watch_out_for_kill_decrease:
            # if client kills are obtainable (when he's alive)
            if self.state == 2 or self.state == 3:
                if visible_player_kills < self.client_last_killcount:
                    print("[Suicide Counter] Suicide occured!")
                    self.watch_out_for_kill_decrease = False
                    self.client_suicides += 1
                    self.redraw_required = True
        
        # finally, if player is alive in the game, record kills for next kill decrease check
        if self.state == 2 or self.state == 3:
            self.client_last_killcount = visible_player_kills
        
        
    
    def getDrawInfo(self):
        #if self.client_suicides == 0:
        #    return None
        
        if not self.redraw_required:
            return None
        self.redraw_required = False
        
        self.draw_info.suicide_count = self.client_suicides
        return self.draw_info