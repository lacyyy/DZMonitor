import time
import random
from os import listdir
from os.path import isfile, join

from PIL import ImageFont
from cv2 import imread, IMREAD_UNCHANGED

from SoundPlayer import Sound
from Visuals import DrawInfoPerRedCutoff, DrawInfoCloseWindow
import util

# CD = countdown, i.e. CD4 = countdown no. 4
# prc = personal redeployment cutoff
# voice message logic:
#   @ end of CD3:
#       "your redeployments stop in X seconds or in X+40 seconds"
#   @ pre-alert during early CD4
#       "your redeployments stop in X seconds if missile countdown is visible, otherwise they stop in X+40 seconds"
#
#   @ PRC before early CD4 start
#       "your redeployments have stopped if missile countdown appears in X seconds, otherwise they stop in 40 seconds"
#   @ PRC during early CD4
#       "your redeployments have stopped if missile countdown is visible, otherwise they stop in 40 seconds"
#
#   @ wave occured at end of early CD4
#       --> disable all redeployment alerts
#   @ during late CD4
#       "your redeployments stop in X seconds"
#   @ if late PRC is definitely active
#       "your redeployments have stopped"
#
#   @ client died and will redeploy sometime after early PRC
#       --> disable all redeployment alerts while dead
#       @ redep after late PRC:
#           "this is your final redeployment {No more excuses./Don't disappoint./Good luck.}"
#       @ redep after early PRC and before late CD4 start:
#           "if missile countdown is visible, this is your final redeployment, otherwise your redeployments stop in X seconds"
#           "if missile countdown appears in X seconds, this is your final redeployment, otherwise your redeployments stop in X seconds"
#       @ redep after CD4 start and before late PRC:
#           --> "your redeployments stop in X seconds" require_alert = True

def GetCurrentRedeploymentDelay(currentdeploymentcount): # in seconds
    return 10 * currentdeploymentcount
def GetNextRedeploymentDelay(currentdeathcount): # in seconds
    return 10 * (currentdeathcount+1)

class RedeploymentCutoff: # personal redeployment cutoff alert
    def __init__(self, folder_path, alert_announcer, enable_alerts, enable_screen):
        self.img_bg   = imread(join(folder_path, "image_background.png"))
        self.img_icon = imread(join(folder_path, "image_icon.png"), IMREAD_UNCHANGED) # load alpha channel
        
        self.icon_pos = util.parseNumberListFromFile([56,3],
            join(folder_path, 'icon_pos_xy.txt'))
        if len(self.icon_pos) >= 2:
            self.icon_pos = (self.icon_pos[0], self.icon_pos[1])
        else:
            self.icon_pos = (56,3)
        
        self.text_font_size = int(util.parseNumberFromFile(33,
            join(folder_path, 'text_size_pixels.txt')))
        self.text_font = ImageFont.truetype(join(folder_path, 'font.ttf'), self.text_font_size)
        
        self.text_pos = util.parseNumberListFromFile([127,40, 195,40, 227,40],
            join(folder_path, 'text_pos_xy.txt'))
        if len(self.text_pos) >= 6:
            self.text_pos = (self.text_pos[0], self.text_pos[1], self.text_pos[2], self.text_pos[3], self.text_pos[4], self.text_pos[5])
        else:
            self.text_pos = (127,40, 195,40, 227,40)
        
        self.text_rgba = util.parseNumberListFromFile([255,255,255],
            join(folder_path, 'text_color_rgb.txt'))
        if len(self.text_rgba) >= 3:
            self.text_rgba = (int(self.text_rgba[0]),int(self.text_rgba[1]),int(self.text_rgba[2]),255)
        else:
            self.text_rgba = (255,255,255,255)
        
        if self.img_bg is not None and self.img_icon is not None:
            icon_bgr = (self.text_rgba[2], self.text_rgba[1], self.text_rgba[0])
            self.img_icon[:,:,0:3] = icon_bgr # set BGR, but keep alpha
            util.overlay_transparent(self.img_bg, self.img_icon, self.icon_pos[0], self.icon_pos[1])
            
            
        self.WINDOW_TITLE = "Personal Redeployment Cutoff - Press ANY key to quit"
        self.draw_info = DrawInfoPerRedCutoff()
        self.draw_info.window_title = self.WINDOW_TITLE
        self.draw_info.image_bg     = self.img_bg
        self.draw_info.image_icon   = self.img_icon
        self.draw_info.icon_pos     = self.icon_pos
        self.draw_info.font         = self.text_font
        self.draw_info.text_rgba    = self.text_rgba
        self.draw_info.text_pos     = self.text_pos
        self.draw_info.text         = ''
        
        self.prev_screen_text = ''
        self.SCREEN_CUTOFF_MESSAGE = 'Over!'
        
        # 0 = client is not a player in a DZ game
        # 1 = client is player in DZ warmup
        # 2 = client is player in live DZ match
        # 3 = client is player in live DZ match and just died (0 HP)
        # 4 = client is player in live DZ match and waits for respawn, watching his mate
        self.state = 0
        self.alerts_enabled = enable_alerts
        self.alerts_paused = False
        self.alert = alert_announcer
        self.alert_required = False
        self.alert_volume = util.parseNumberFromFile(1.0,
            join(folder_path, 'alert_volume.txt'))
        # alert sound
        self.snd_alert_tune = Sound(join(folder_path, 'alert_tune.wav'))
        # voice line sounds
        self.snd_vl_redep_stop           = Sound(join(folder_path, 'voice_lines', 'redep_stop.wav'))
        self.snd_vl_redep_have_stopped   = Sound(join(folder_path, 'voice_lines', 'redep_have_stopped.wav'))
        self.snd_vl_if_cd_appears        = Sound(join(folder_path, 'voice_lines', 'if_cd_appears.wav'))
        self.snd_vl_if_cd_visible        = Sound(join(folder_path, 'voice_lines', 'if_cd_visible.wav'))
        self.snd_vl_or                   = Sound(join(folder_path, 'voice_lines', 'or.wav'))
        self.snd_vl_otherwise_they_stop  = Sound(join(folder_path, 'voice_lines', 'otherwise_they_stop.wav'))
        self.snd_vl_otherwise_redep_stop = Sound(join(folder_path, 'voice_lines', 'otherwise_redep_stop.wav'))
        # final redeployment voice line sounds
        self.snd_vl_final_redep_definitive = Sound(join(folder_path, 'voice_lines', 'final_redep_definitive.wav'))
        self.snd_vl_final_redep_msgs = []
        try:
            msg_folder_path = join(folder_path, 'voice_lines', 'final_redep_msg')
            final_redep_msg_file_list = [f for f in listdir(msg_folder_path) if isfile(join(msg_folder_path, f))]
            for msg_file_name in final_redep_msg_file_list:
                if msg_file_name.lower().endswith('.wav'):
                    snd = Sound(join(msg_folder_path, msg_file_name))
                    self.snd_vl_final_redep_msgs.append(snd)
        except OSError:
            self.snd_vl_final_redep_msgs = []
            util.report_error("Failed to load 'personal_redeployment_cutoff\voice_lines\final_redep_msg'")
        
        self.necessary_snds_loaded = (True and
            self.snd_alert_tune               .is_loaded() and
            self.snd_vl_redep_stop            .is_loaded() and
            self.snd_vl_redep_have_stopped    .is_loaded() and
            self.snd_vl_if_cd_appears         .is_loaded() and
            self.snd_vl_if_cd_visible         .is_loaded() and
            self.snd_vl_or                    .is_loaded() and
            self.snd_vl_otherwise_they_stop   .is_loaded() and
            self.snd_vl_otherwise_redep_stop  .is_loaded() and
            self.snd_vl_final_redep_definitive.is_loaded())
        
        # hardcoded, too complicated for user control
        self.alert_times_early_rc = [90, 30]
        self.alert_times_late_rc  = [30]
        self.last_alerted_time_early_rc = None
        self.last_alerted_time_late_rc  = None
        self.cd3_end_checked = False
        self.early_prc_happened = False # early personal redeployment cutoff
        self.late_prc_happened  = False # late personal redeployment cutoff
        
        self.match_start = None
        self.teammate_id = None # when playing solo, this is an enemy
        self.client_deployments = None
        self.client_deaths = None
        self.client_last_death = None # time of last client's death
        self.client_last_score = None
        self.client_last_money = None
        self.is_client_ingame = False
        self.is_client_spectating = False
        self.visible_player_score_prev = None
        self.visible_player_money_prev = None
        self.wave_check_triggered = False
        self.wave_check_min_score = None
        self.wave_times = []
        self.last_gamestate_time = None
        
        if not self.necessary_snds_loaded:
            util.report_error("Failed to load necessary sound files for redeployment cutoff alerts.")
            self.alerts_enabled = False
        
    # state machine
    def update(self, next_gamestate):
        if next_gamestate is None:
            return
        
        # helper states
        gamestate_time = next_gamestate.receive_time
        game_mode = next_gamestate.get("map","mode")
        map_phase = next_gamestate.get("map","phase")
        round     = next_gamestate.get("map","round")
        client_id = next_gamestate.get("provider","steamid")
        activity  = next_gamestate.get("player","activity")
        visible_player_id     = next_gamestate.get("player","steamid")
        visible_player_health = next_gamestate.get("player","state","health")
        visible_player_deaths = next_gamestate.get("player","match_stats","deaths")
        visible_player_score  = next_gamestate.get("player","match_stats","score")
        visible_player_money  = next_gamestate.get("player","state","money")
        
        self.is_client_spectating = client_id != visible_player_id
        
        # interesting state transitions
        state_trans_has_client_just_died         = False
        state_trans_has_client_just_redeployed   = False # redeployed after a death
        state_trans_just_started_spectating_mate = False
        
        # branches to base state
        if (    next_gamestate.get("map","mode") != 'survival' or
                next_gamestate.get("map","phase") == 'gameover' or
                next_gamestate.get("map","round") == 1):
            self.state = 0
        
        # switch statement
        
        # 0: client is not a player in a DZ game
        if self.state == 0:
            if (not self.is_client_spectating and game_mode == 'survival' and
                    map_phase == 'warmup'):
                self.state = 1
            # Only leave base state through warmup because we need to
            # know the time when the match starts. This is the only way.
        # 1: client is player in DZ warmup
        elif self.state == 1:
            if (not self.is_client_spectating and map_phase == 'live' and
                    visible_player_health > 0):
                self.alerts_paused = False
                self.match_start = gamestate_time
                self.client_deployments = 1
                self.client_deaths = 0
                self.teammate_id = None
                self.client_last_death = None
                self.visible_player_score_prev = None
                self.visible_player_money_prev = None
                self.wave_check_triggered = False
                self.wave_times = []
                self.alert_required = False
                self.last_alerted_time_early_rc = None
                self.last_alerted_time_late_rc  = None
                self.cd3_end_checked = False
                self.early_prc_happened = False
                self.late_prc_happened = False
                self.state = 2
        # 2: client is player in live DZ match
        elif self.state == 2:
            if not self.is_client_spectating and visible_player_health == 0:
                self.client_last_death = gamestate_time
                state_trans_has_client_just_died = True
                self.state = 3
        # 3: client is player in live DZ match and just died (0 HP)
        elif self.state == 3:
            # If client just died and then sees himself with health, he's watching his suicide -> game over
            if not self.is_client_spectating and visible_player_health > 0:
                self.state = 0
            # If we started spectating our alive teammate
            elif (self.is_client_spectating and visible_player_health > 0 and
                    (self.teammate_id is None or self.teammate_id == visible_player_id)):
                self.teammate_id = visible_player_id
                state_trans_just_started_spectating_mate = True
                self.state = 4
            # We started spectating our teammate or enemy and he just died -> game over
            elif self.is_client_spectating and visible_player_health == 0:
                self.state = 0
            # We started spectating an enemy -> game is over
            elif (self.is_client_spectating and self.teammate_id is not None and 
                    self.teammate_id != visible_player_id):
                self.state = 0
        # 4: client is player in live DZ match and waits for respawn, watching his mate
        elif self.state == 4:
            if self.is_client_spectating and visible_player_health == 0:
                self.state = 0
            # We started spectating an enemy -> game is over
            elif (self.is_client_spectating and self.teammate_id is not None and 
                    self.teammate_id != visible_player_id):
                self.state = 0
            elif not self.is_client_spectating:
                state_trans_has_client_just_redeployed = True
                self.state = 2
            # If client spectated longer than his waiting time till respawn -> recognize game over
            elif (self.is_client_spectating and
                    gamestate_time - self.client_last_death > 2.0 + GetCurrentRedeploymentDelay(self.client_deployments)):
                self.state = 0;
        
        # first, handle important state transition actions
        if state_trans_has_client_just_died: # count deaths
            self.client_deaths += 1
        if state_trans_has_client_just_redeployed: # count redeployments
            self.client_deployments += 1
        
        # do things depending on current state
        self.is_client_ingame = self.state >= 2 and self.state <= 4
        
        # check if new missile wave occured
        if self.is_client_ingame:
            if state_trans_just_started_spectating_mate:
                # reset money score check for teammate
                self.visible_player_score_prev = None
                self.visible_player_money_prev = None
                self.wave_check_triggered = False
            
            if state_trans_has_client_just_redeployed:
                # reset money score check for client respawn
                self.visible_player_score_prev = None
                self.visible_player_money_prev = None
                self.wave_check_triggered = False
            
            if not self.wave_check_triggered:
                if self.visible_player_money_prev is not None and self.visible_player_score_prev is not None:
                    if visible_player_money - self.visible_player_money_prev >= 750:
                        self.wave_check_min_score = self.visible_player_score_prev + int(750 / 50)
                        if visible_player_score < self.wave_check_min_score:
                            self.wave_check_triggered = True
                        else:
                            print(int(gamestate_time - self.match_start), "[WAVE CHECK] False Alarm")
            else:
                if visible_player_score < self.wave_check_min_score:
                    self.wave_times.append(self.last_gamestate_time)
                    print(int(gamestate_time - self.match_start), "[WAVE CHECK] wave no.", str(len(self.wave_times)))
                else:
                    print(int(gamestate_time - self.match_start), "[WAVE CHECK] False Alarm")
                self.wave_check_triggered = False
        
        if (self.state == 0 or self.state == 1 or len(self.wave_times) < 3 or
                map_phase == 'warmup' or activity == 'menu'):
            self.draw_info.text = '' # don't show screen
        elif len(self.wave_times) >= 4:
            self.draw_info.text = self.SCREEN_CUTOFF_MESSAGE
        # only start alerting after third wave ended, stop alerting after fourth wave ended
        elif self.is_client_ingame and len(self.wave_times) == 3:
            nextRedepDelay = GetNextRedeploymentDelay(self.client_deaths)
            time_till_cutoff_early = ((self.wave_times[2] + 100) - gamestate_time) - nextRedepDelay
            time_till_cutoff_late  = ((self.wave_times[2] + 145) - gamestate_time) - nextRedepDelay
            time_since_cd3_end = gamestate_time - self.wave_times[2]
            
            if self.draw_info.text != self.SCREEN_CUTOFF_MESSAGE:
                # screen text
                ttce_mins = int(max(0, time_till_cutoff_early) / 60.0)
                ttce_secs = int(max(0, time_till_cutoff_early) % 60.0)
                ttcl_mins = int(max(0, time_till_cutoff_late ) / 60.0)
                ttcl_secs = int(max(0, time_till_cutoff_late ) % 60.0)
                
                self.draw_info.text  = str(ttce_mins) + ':0' + str(ttce_secs) + ' or ' if (ttce_secs < 10) else str(ttce_mins) + ':' + str(ttce_secs) + ' or '
                self.draw_info.text += str(ttcl_mins) + ':0' + str(ttcl_secs) if (ttcl_secs < 10) else str(ttcl_mins) + ':' + str(ttcl_secs)
            
            # if client just died and might be going to redeploy for the last time
            if state_trans_has_client_just_died:
                if GetCurrentRedeploymentDelay(self.client_deployments) >= time_till_cutoff_early:
                    # disable all alerts until next redeployment
                    self.alerts_paused = True
                    self.alert_required = False
            # if client redeployed and alerts were paused -> an alert is necessary
            if state_trans_has_client_just_redeployed:
                if self.alerts_paused: # unpause alerts
                    self.early_prc_happened = True # mark early prc as handled
                    if time_till_cutoff_late < 0: # after late personal redeployment cutoff
                        self.late_prc_happened = True # mark late prc as handled
                        self.alerts_paused = True # Stop all alerts until end of match
                        self.draw_info.text = self.SCREEN_CUTOFF_MESSAGE
                        # "(tune) this is your final redeployment {No more excuses./Don't disappoint./Good luck.}"
                        snd_list = [self.snd_alert_tune, self.snd_vl_final_redep_definitive]
                        if len(self.snd_vl_final_redep_msgs) > 0:
                            rand_idx = random.randrange(len(self.snd_vl_final_redep_msgs))
                            snd_list.append(self.snd_vl_final_redep_msgs[rand_idx])
                        if self.alerts_enabled:
                            self.alert.scheduleSequentialSounds(snd_list, self.alert_volume)
                    elif time_since_cd3_end > 100: # before late prc, after early countdown 4
                        self.alerts_paused = False # allow alerts again
                        self.alert_required = True # regular "(tune) your redeployments stop in X seconds"
                    else: # after early personal redeployment cutoff, before late countdown 4
                        self.alerts_paused = False  # allow alerts again
                        snd_list = []
                        # differentiate if early countdown 4 could be visible
                        if time_since_cd3_end >= (55 - 3.5): # 3.5 seconds tolerance
                            snd_list.append(self.snd_alert_tune)                # (tune)
                            snd_list.append(self.snd_vl_if_cd_visible)          # if missile countdown is visible,
                            snd_list.append(self.snd_vl_final_redep_definitive) # this is your final redeployment,
                            snd_list.append(self.snd_vl_otherwise_redep_stop)   # otherwise your redeployments stop
                            snd_list.append(self.alert.getBestTimeLeftSound(max(5, time_till_cutoff_late))) # in X seconds
                        else:
                            snd_list.append(self.snd_alert_tune)                # (tune)
                            snd_list.append(self.snd_vl_if_cd_appears)          # if missile countdown appears
                            snd_list.append(self.alert.getBestTimeLeftSound(max(5, 55 - time_since_cd3_end))) # in X seconds,
                            snd_list.append(self.snd_vl_final_redep_definitive) # this is your final redeployment,
                            snd_list.append(self.snd_vl_otherwise_redep_stop)   # otherwise your redeployments stop
                            snd_list.append(self.alert.getBestTimeLeftSound(max(5, time_till_cutoff_late))) # in X seconds
                        if self.alerts_enabled:
                            self.alert.scheduleSequentialSounds(snd_list, self.alert_volume)
            
            # if regular alerts are currently allowed to be played
            if not self.alerts_paused:
                # if there are definitely no more redeployments
                if time_till_cutoff_late < 0:
                    if not self.late_prc_happened:
                        self.late_prc_happened = True
                        self.draw_info.text = self.SCREEN_CUTOFF_MESSAGE
                        # "(tune) your redeployments have stopped"
                        snd_list = [self.snd_alert_tune, self.snd_vl_redep_have_stopped]
                        if self.alerts_enabled:
                            self.alert.scheduleSequentialSounds(snd_list, self.alert_volume)
                        self.alerts_paused = True # Stop all alerts until end of match
                    
                # if there could still be redeployments
                else:
                    # early cutoff alert logic
                    if time_till_cutoff_early > 0:
                        # if countdown 3 has just ended, check if alert is required once
                        if not self.cd3_end_checked:
                            self.cd3_end_checked = True
                            closest_alert_time = None
                            for t in self.alert_times_early_rc:
                                if closest_alert_time is None:
                                    closest_alert_time = t
                                elif abs(t - time_till_cutoff_early) < abs(closest_alert_time - time_till_cutoff_early):
                                    closest_alert_time = t
                            if closest_alert_time is not None and closest_alert_time > time_till_cutoff_early:
                                self.alert_required = True
                        
                        # check regularly if new alert is due
                        if not self.alert_required:
                            for at in self.alert_times_early_rc:
                                if self.last_alerted_time_early_rc is None or at < self.last_alerted_time_early_rc:
                                    if abs(at - time_till_cutoff_early) < 0.5:
                                        self.alert_required = True
                                        break
                        
                        # find fitting voice message for required alert, fail -> try later
                        if self.alert_required:
                            usable_alert_times = self.alert.getTimeLeftList()
                            for uat in usable_alert_times:
                                if uat > 4 and abs(time_till_cutoff_early - uat) < 0.5: # (uat > 4) to block uat=0 sound
                                    snd_time_left_cutoff_early = self.alert.getBestTimeLeftSound(uat)
                                    snd_time_left_cutoff_late  = self.alert.getBestTimeLeftSound(uat+40)
                                    # "(tune) your redeployments stop in X seconds [...]" 
                                    snd_list = [self.snd_alert_tune, self.snd_vl_redep_stop, snd_time_left_cutoff_early]
                                    # differentiate if early countdown 4 could be visible
                                    if time_since_cd3_end >= (55 - 3.5): # 3.5 seconds tolerance
                                        # "[...] if missile countdown is visible, otherwise they stop in X+40 seconds"
                                        snd_list.append(self.snd_vl_if_cd_visible)
                                        snd_list.append(self.snd_vl_otherwise_they_stop)
                                        snd_list.append(snd_time_left_cutoff_late)
                                    else:
                                        # "[...] or in X+40 seconds"
                                        snd_list.append(self.snd_vl_or)
                                        snd_list.append(snd_time_left_cutoff_late)
                                    if self.alerts_enabled:
                                        self.alert.scheduleSequentialSounds(snd_list, self.alert_volume)
                                    self.last_alerted_time_early_rc = uat
                                    self.alert_required = False
                                    break
                    
                    # if early personal redeployment cutoff possibly occured
                    if not self.early_prc_happened and time_till_cutoff_early < 0:
                        self.early_prc_happened = True
                        # "(tune) your redeployments have stopped [...]"
                        snd_list = [self.snd_alert_tune, self.snd_vl_redep_have_stopped]
                        # differentiate if early countdown 4 could be visible
                        if time_since_cd3_end >= (55 - 3.5): # 3.5 seconds tolerance
                            # "[...] if missile countdown is visible, otherwise they stop in 40 seconds"
                            snd_list.append(self.snd_vl_if_cd_visible)
                            snd_list.append(self.snd_vl_otherwise_they_stop)
                            snd_list.append(self.alert.getBestTimeLeftSound(40))
                        else:
                            # "[...] if missile countdown appears in X seconds, otherwise they stop in 40 seconds"
                            snd_list.append(self.snd_vl_if_cd_appears)
                            snd_list.append(self.alert.getBestTimeLeftSound(max(5, 55 - time_since_cd3_end)))
                            snd_list.append(self.snd_vl_otherwise_they_stop)
                            snd_list.append(self.alert.getBestTimeLeftSound(40))
                        if self.alerts_enabled:
                            self.alert.scheduleSequentialSounds(snd_list, self.alert_volume)
                        self.alert_required = False
                    
                    
                    # late cutoff alert logic
                    if time_since_cd3_end > 100 and time_till_cutoff_late > 0: # late countdown starts at t=100
                        # check regularly if new alert is due
                        if not self.alert_required:
                            for at in self.alert_times_late_rc:
                                if self.last_alerted_time_late_rc is None or at < self.last_alerted_time_late_rc:
                                    if abs(at - time_till_cutoff_late) < 0.5:
                                        self.alert_required = True
                                        break
                        
                        # find fitting voice message for required alert, fail -> try later
                        if self.alert_required:
                            usable_alert_times = self.alert.getTimeLeftList()
                            for uat in usable_alert_times:
                                if uat > 4 and abs(time_till_cutoff_late - uat) < 0.5: # (uat > 4) to block uat=0 sound
                                    snd_time_left = self.alert.getBestTimeLeftSound(uat)
                                    # "(tune) your redeployments stop in X seconds" 
                                    snd_list = [self.snd_alert_tune, self.snd_vl_redep_stop, snd_time_left]
                                    if self.alerts_enabled:
                                        self.alert.scheduleSequentialSounds(snd_list, self.alert_volume)
                                    self.last_alerted_time_late_rc = uat
                                    self.alert_required = False
                                    break
        
        self.visible_player_score_prev = visible_player_score
        self.visible_player_money_prev = visible_player_money
        self.last_gamestate_time = gamestate_time
    
    def getDrawInfo(self):
        # don't redraw if text didn't change
        if self.draw_info.text == self.prev_screen_text:
            return None
        
        # check if window should be closed
        if self.draw_info.text == '' and self.prev_screen_text != '':
            draw_info_close_win = DrawInfoCloseWindow()
            draw_info_close_win.window_title = self.WINDOW_TITLE
            self.prev_screen_text = ''
            return draw_info_close_win
        
        # redraw
        self.prev_screen_text = self.draw_info.text
        return self.draw_info