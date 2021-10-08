import sys
import traceback
import time
import threading
import copy
from queue import Queue
from queue import Empty as QEmpty
from PIL import ImageDraw, Image
import numpy as np
import cv2

import Constants

class DrawInfoBase:
    def __init__(self, redraw_regularly):
        self.redraw_regularly = redraw_regularly

class DrawInfoCloseWindow(DrawInfoBase):
    def __init__(self):
        super().__init__(redraw_regularly=False)
        self.window_title = None

class DrawInfoWindowImage(DrawInfoBase):
    def __init__(self):
        super().__init__(redraw_regularly=False)
        self.window_title = None
        self.img          = None

class DrawInfoPerRedCutoff(DrawInfoBase):
    def __init__(self):
        super().__init__(redraw_regularly=False)
        self.window_title  = None
        self.image_bg      = None
        self.font          = None
        self.text          = None
        self.text_rgba     = None
        self.text_pos      = None

class DrawInfoSuicideCounter(DrawInfoBase):
    def __init__(self):
        super().__init__(redraw_regularly=True)
        self.suicide_count = None
        self.image_bg      = None
        self.font          = None
        self.text_rgba     = None
        self.text_pos      = None

class DrawInfoMapCycle(DrawInfoBase):
    def __init__(self):
        super().__init__(redraw_regularly=False)
        self.seconds_till_next_map = None
        self.map_name_current      = None
        self.map_name_next         = None
        self.map_image_current     = None
        self.map_image_next        = None
        self.font                  = None
        self.text_rgba             = None
        self.text_pos              = None
        
def draw_from_draw_info(info):
    info_type = type(info)
    
    if info_type is DrawInfoCloseWindow:
        try:
            cv2.destroyWindow(info.window_title)
        except cv2.error: # thrown if window is already closed
            pass
    
    elif info_type is DrawInfoWindowImage:
        cv2.imshow(info.window_title, info.img)
    
    elif info_type is DrawInfoPerRedCutoff:
        pil_img_bg = Image.fromarray(cv2.cvtColor(info.image_bg  ,cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img_bg)
        parts = info.text.split()
        for i in range(len(parts)):
            pos = (info.text_pos[i*2],info.text_pos[i*2+1])
            draw.text(pos, parts[i], font=info.font, fill=info.text_rgba, anchor='ls')
        img = cv2.cvtColor(np.array(pil_img_bg), cv2.COLOR_RGB2BGR)
        cv2.imshow(info.window_title, img)
    
    elif info_type is DrawInfoSuicideCounter:
        text = "Suicides: " + str(info.suicide_count)
        img = cv2.cvtColor(info.image_bg,cv2.COLOR_BGR2RGB)
        pil_im = Image.fromarray(img)
        draw = ImageDraw.Draw(pil_im)
        draw.text(info.text_pos, text, font=info.font, fill=info.text_rgba)
        img = cv2.cvtColor(np.array(pil_im), cv2.COLOR_RGB2BGR)
        cv2.imshow("Suicide Counter - Press ANY key to quit", img)
    
    elif info_type is DrawInfoMapCycle:
        clockTextTillNextMap = time.strftime("%M:%S", time.gmtime(info.seconds_till_next_map))
        text = "Active Map " + info.map_name_current + " | Next Map " + info.map_name_next + " in " + clockTextTillNextMap
        img = cv2.cvtColor(info.map_image_current,cv2.COLOR_BGR2RGB)
        pil_im = Image.fromarray(img)
        draw = ImageDraw.Draw(pil_im)
        draw.text(info.text_pos, text, font=info.font, fill=info.text_rgba)
        img = cv2.cvtColor(np.array(pil_im), cv2.COLOR_RGB2BGR)
        cv2.imshow("Map Cycle - Press ANY key to quit", img)

def thread_function(visualsQ, keyPressQ, FPS):
    frame_time = 1 / FPS
    draw_info_list = []
    last_draw_start = None
    
    running = True
    while running:
        # Get new draw information
        while visualsQ.qsize() > 0:
            try:
                next_draw_info = visualsQ.get_nowait()
                
                # End thread
                if next_draw_info == 'QUIT' or next_draw_info is None:
                    running = False
                    break
                
                if next_draw_info.redraw_regularly:
                    # Add new info and remove old info (if existent)
                    for i in range(len(draw_info_list)):
                        if type(draw_info_list[i]) is type(next_draw_info):
                            del draw_info_list[i]
                            break
                    draw_info_list.append(next_draw_info)
                else:
                    draw_from_draw_info(next_draw_info)
            except QEmpty:
                break
        
        if not running:
            break
        
        # Draw everything if new frame is required
        current_time = time.perf_counter()
        if last_draw_start is None or current_time - last_draw_start >= frame_time:
            try:
                last_draw_start = current_time
                for x in draw_info_list:
                    draw_from_draw_info(x)
            except Exception:
                traceback.print_exc(file=sys.stdout)
                keyPressQ.put(32) # 32 is spacebar
                running = False
                break
        
        # Display windows and listen for key presses
        key_pressed = cv2.waitKey(5)
        if key_pressed != -1:
            print('KEY PRESSED:', key_pressed)
            keyPressQ.put(key_pressed)
    
    cv2.destroyAllWindows()
    print('[Graphics] Thread terminated.')
    

class Visuals:
    def __init__(self, FPS):
        self.FPS = min(max(0.1, FPS), 60)
        self.q = Queue()
        self.key_press_q = Queue()
        self.thread = threading.Thread(target=thread_function, args=(self.q,self.key_press_q,self.FPS))
        self.thread.start()
    
    def update(self, draw_info):
        if draw_info is not None and draw_info != 'QUIT':
            self.q.put(copy.copy(draw_info))
    
    def cleanup(self):
        print("[Graphics] Stopping thread...")
        self.q.put('QUIT')
        self.thread.join()
    
    def getReceivedKeyPress(self):
        try:
            next_key_press = self.key_press_q.get_nowait()
            return next_key_press
        except QEmpty:
            return None