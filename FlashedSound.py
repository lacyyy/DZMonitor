from os.path import join

from SoundPlayer import Sound
import util

class FlashedSound:
    def __init__(self, folder_path, sound_player, enable):
        self.player = sound_player
        self.enabled = enable
        self.min_flashed_val = 0.01 * util.parseNumberFromFile(70.0,
            join(folder_path, 'min_flashed_percentage.txt'))
        self.snd = Sound(join(folder_path, 'flashed_sound.wav'))
        self.sound_volume = util.parseNumberFromFile(0.9,
            join(folder_path, 'sound_volume.txt'))
        self.last_flashed_val = None
        
        if self.snd is None:
            self.enabled = False
    
    
    def update(self, next_gamestate):
        if next_gamestate is None:
            return
        if not self.enabled:
            return True
        
        flashed_val = next_gamestate.get("player","state","flashed")
        
        if flashed_val is not None:
            if self.last_flashed_val is None or flashed_val > self.last_flashed_val:
                if (flashed_val / 255.0) >= self.min_flashed_val:
                    self.player.stopSound(self.snd)
                    self.player.playSound(self.snd, self.sound_volume)
        
        self.last_flashed_val = flashed_val