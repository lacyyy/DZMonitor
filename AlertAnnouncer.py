import time
from os import listdir
from os.path import isfile, join

from SoundPlayer import Sound
import util

class AlertAnnouncer:
    
    def __init__(self, folder_path, sound_player):
        self.fail        = False
        self.folder_path = folder_path
        self.player      = sound_player
        self.earliest_alert_schedule_time = None
        
        # Load sound files
        self.snd_list_time_left = []
        self.time_left_list = []
        
        dir_path_snd_time_left = join(self.folder_path, 'alert_time_left/')
        try:
            dir_contents = listdir(dir_path_snd_time_left)
            files = [f for f in dir_contents if isfile(join(dir_path_snd_time_left, f))]
            
            prefix = 'alert_time_left_'
            suffix = '.wav'
            for file in files:
                if file.lower().startswith(prefix) and file.lower().endswith(suffix):
                    try:
                        number = int(file[len(prefix):-len(suffix)])
                        self.snd_list_time_left.append([number, Sound(join(dir_path_snd_time_left, file))])
                        self.time_left_list.append(number)
                    except (ValueError, OSError):
                        continue
            self.time_left_list.sort()
            
            if len(self.snd_list_time_left) == 0:
                util.report_error("Alert announcer can't function without alert_time_left_X.wav files in " + dir_path_snd_time_left)
                self.fail = True
                return
            
        except FileNotFoundError:
            util.report_error("Folder Not Found: " + dir_path_snd_time_left + " : alert announcer can't function")
            self.fail = True
            return
    
    def scheduleSequentialSounds(self, snd_list, volume=1.0):
        if self.fail:
            return
        
        cur_time = time.perf_counter()
        if (self.earliest_alert_schedule_time is not None and
                cur_time < self.earliest_alert_schedule_time):
            play_time = self.earliest_alert_schedule_time
        else:
            play_time = cur_time
        
        # queue sounds
        acc_snd_length = 0
        for snd in snd_list:
            self.player.playSound(snd, volume, play_time - cur_time + acc_snd_length)
            acc_snd_length += snd.length
        self.earliest_alert_schedule_time = play_time + acc_snd_length + 1.5
    
    def alertEvent(self, snd_event_name, time_left_till_event, volume=1.0, pre_tune=None):
        if self.fail:
            return
        
        # Find closest time left voice line
        snd_time_left = self.getBestTimeLeftSound(time_left_till_event)
        
        sounds = [snd_event_name, snd_time_left]
        if pre_tune is not None:
            sounds.insert(0, pre_tune)
        self.scheduleSequentialSounds(sounds, volume)
    
    def getTimeLeftList(self):
        return self.time_left_list
    
    def getBestTimeLeftSound(self, time_left):
        # Find closest time left voice line
        best_idx = None
        best_dist = None
        for i in range(len(self.snd_list_time_left)):
            dist = abs(time_left - self.snd_list_time_left[i][0])
            if best_idx is None or dist < best_dist:
                best_idx = i
                best_dist = dist
        return self.snd_list_time_left[best_idx][1]