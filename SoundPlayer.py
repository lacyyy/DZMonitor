import time
import threading
from queue import Queue
from queue import Empty as QEmpty
import pygame
import util

class Sound:
    def __init__(self, filepath):
        try:
            self.sound = pygame.mixer.Sound(file=filepath)
            self.length = self.sound.get_length()
        except FileNotFoundError:
            self.sound = None
            self.length = None
            util.report_error("FileNotFound: " + filepath)
    def is_loaded(self):
        return self.sound is not None

class PlayCommand:
    def __init__(self, sound, volume, timestamp):
        self.sound = sound
        self.volume = volume
        self.timestamp = timestamp

class StopCommand:
    def __init__(self, sound, timestamp):
        self.sound = sound
        self.timestamp = timestamp

def thread_function(soundQ):
    running = True
    
    delayed_msgs = []
    active_sounds = []
    while running:
        cur_time = time.perf_counter()
        try:
            # Check if any sounds stopped playing
            finished = []
            for i in range(len(active_sounds)):
                if cur_time > active_sounds[i][0]:
                    finished.append(i)
            for idx in finished:
                del active_sounds[idx]
            
            # Check if any delayed message is due
            due_msg_idx = None
            for i in range(len(delayed_msgs)):
                if cur_time >= delayed_msgs[i][0] :
                    if due_msg_idx is None:
                        due_msg_idx = i
                    # Prefer older messages
                    elif delayed_msgs[i][0] < delayed_msgs[due_msg_idx][0]:
                        due_msg_idx = i
            
            # Get delayed message or check for new ones
            if due_msg_idx is not None:
                next_msg = delayed_msgs[due_msg_idx][1]
                del delayed_msgs[due_msg_idx]
            else:
                next_msg = soundQ.get_nowait()
            
            # End thread
            if next_msg == 'QUIT':
                running = False
                break
            
            action = next_msg[0]
            
            if action == 'PLAY':
                play_cmd = next_msg[1]
                if cur_time >= play_cmd.timestamp:
                    play_cmd.sound.sound.set_volume(play_cmd.volume)
                    play_cmd.sound.sound.play()
                    active_sounds.append([time.perf_counter()+play_cmd.sound.length, play_cmd.sound])
                else:
                    delayed_msgs.append([play_cmd.timestamp, next_msg])
            elif action == 'STOP':
                stop_cmd = next_msg[1]
                if cur_time >= stop_cmd.timestamp:
                    for i in range(len(active_sounds)):
                        if stop_cmd.sound == active_sounds[i][1]:
                            stop_cmd.sound.sound.stop()
                            del active_sounds[i]
                            break
                else:
                    delayed_msgs.append([play_cmd.timestamp, next_msg])
            
        except QEmpty:
            time.sleep(0.01)



class SoundPlayer:
    
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        
        if pygame.mixer.get_init():
            print('[Sound Player] Loaded!')
            self.fail = False
        else:
            util.report_error('[Sound Player] Failed to load!')
            self.fail = True
            return
        
        self.soundQ = Queue()
        self.thread = threading.Thread(target=thread_function, args=(self.soundQ,))
        self.thread.start()
    
    def playSound(self, sound, volume, delay=0.0):
        if self.fail or volume < 0.0:
            return
        
        t = time.perf_counter()
        timestamp = t + delay
        self.soundQ.put(['PLAY', PlayCommand(sound, volume, timestamp)])
    
    def stopSound(self, sound, delay=0.0):
        if self.fail:
            return
        
        t = time.perf_counter()
        timestamp = t + delay
        self.soundQ.put(['STOP', StopCommand(sound, timestamp)])
    
    def cleanup(self):
        print("[Sound Player] Stopping thread...")
        
        if not self.fail:
            self.soundQ.put('QUIT')
            self.thread.join()
        
        print("[Sound Player] Thread stopped!")
        pygame.mixer.quit()
        pygame.quit()
    