import time
from os import listdir
from os.path import isdir, join
from datetime import datetime
from datetime import timezone
from PIL import ImageFont
from cv2 import imread

from SoundPlayer import Sound
from Visuals import DrawInfoMapCycle
import util

class Map:
    def __init__(self, name, folder_path):
        self.name = name
        self.duration = util.parseNumberFromFile(540.0,
            join(folder_path, 'duration_seconds.txt'))
        self.image = imread(join(folder_path, "image.png"))
        self.snd_name = Sound(join(folder_path, 'alert_map_name.wav'))
        self.alert_volume = util.parseNumberFromFile(0.5,
            join(folder_path, 'alert_volume.txt'))
        self.alert_times = util.parseNumberListFromFile([],
            join(folder_path, 'alert_times_seconds.txt'))


class MapCycle:
    def __init__(self, folder, alert_announcer, enable_alerts):
        
        self.client_in_dz_match = False
        self.alerts_enabled = enable_alerts
        if self.alerts_enabled:
            self.alert = alert_announcer
            self.alert_next_map_required = False
            self.last_alert_time = None
            self.last_map_active_alert = 0
            self.snd_alert_tune = Sound(join(folder, 'alert_tune.wav'))
        self.last_drawn_clock_time = None
        self.utc_offset = util.parseNumberFromFile(0.0,
            join(folder, 'utc_offset_seconds.txt'))
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
        
        try:
            subdirectories = [f for f in listdir(folder) if isdir(join(folder, f))]
            subdirectories.sort()
        except OSError: # no folders found
            subdirectories = []
            util.report_error("No map cycle folders found.")
        
        self.maps_ordered = []
        self.cycle_length = 0
        for map_folder in subdirectories:
            map_name = map_folder.split('_')[-1].capitalize()
            if map_name == '':
                util.report_error("Couldn't parse folder " + join(folder, map_folder)
                    + ": Has to follow the naming scheme: X_dz_something")
                continue
            
            map = Map(map_name, join(folder, map_folder))
            self.maps_ordered.append(map)
            self.cycle_length += map.duration
        
        self.current_map           = None
        self.next_map              = None
        self.seconds_till_next_map = None
        
        self.update(None)
    
    def update(self, next_gamestate):
        if len(self.maps_ordered) == 0:
            self.current_map           = None
            self.next_map              = None
            self.seconds_till_next_map = None
            return
        
        if next_gamestate is not None:
            self.client_in_dz_match = next_gamestate.get("map","mode") == 'survival'
        
        secondsIntoCycle = ((datetime.now(timezone.utc)-datetime.fromtimestamp(self.utc_offset, tz=timezone.utc)).total_seconds()) % self.cycle_length
        
        # Determine index of current map
        current_map_idx = None
        prevMapsDuration = 0
        for i in range(len(self.maps_ordered)):
            if secondsIntoCycle <= prevMapsDuration + self.maps_ordered[i].duration + 0.001:
                current_map_idx = i
                break
            prevMapsDuration += self.maps_ordered[i].duration
        
        # Determine current and next map
        self.current_map = self.maps_ordered[current_map_idx]
        next_map_idx = (current_map_idx+1) % len(self.maps_ordered)
        self.next_map = self.maps_ordered[next_map_idx];
        
        # Determine time left until next map
        secondsIntoMap = secondsIntoCycle - prevMapsDuration
        self.seconds_till_next_map = self.maps_ordered[current_map_idx].duration - secondsIntoMap
        
        # next map alert
        if self.alerts_enabled:
            if self.next_map.snd_name.is_loaded() and self.snd_alert_tune.is_loaded():
                if self.next_map.alert_times is not None:
                    if not self.alert_next_map_required:
                        for at in self.next_map.alert_times:
                            if abs(self.seconds_till_next_map - at) < 0.5:
                                if at == 0:
                                    if time.perf_counter() - self.last_map_active_alert > 10.0:
                                        if self.client_in_dz_match:
                                            self.alert.alertEvent(self.next_map.snd_name, 0, self.next_map.alert_volume, self.snd_alert_tune)
                                        self.last_map_active_alert = time.perf_counter()
                                        break
                                elif self.last_alert_time is None or time.perf_counter() - self.last_alert_time > 5.0:
                                    self.alert_next_map_required = True
                                    break
                    
                    if self.alert_next_map_required:
                        usable_alert_times = self.alert.getTimeLeftList()
                        
                        for uat in usable_alert_times:
                            if abs(self.seconds_till_next_map - uat) < 0.5:
                                if self.client_in_dz_match:
                                    self.alert.alertEvent(self.next_map.snd_name, uat, self.next_map.alert_volume, self.snd_alert_tune)
                                self.alert_next_map_required = False
                                self.last_alert_time = time.perf_counter()
                                break
    
    def getDrawInfo(self):
        if len(self.maps_ordered) == 0:
            return None
        if self.last_drawn_clock_time is not None and int(self.seconds_till_next_map) == self.last_drawn_clock_time:
            return None
        
        info = DrawInfoMapCycle()
        info.seconds_till_next_map = self.seconds_till_next_map
        info.map_name_current      = self.current_map.name
        info.map_name_next         = self.next_map.name
        info.map_image_current     = self.current_map.image
        info.map_image_next        = self.next_map.image
        info.font                  = self.text_font
        info.text_rgba             = self.text_rgba
        info.text_pos              = self.text_pos
        
        self.last_drawn_clock_time = int(info.seconds_till_next_map)
        return info