from cv2 import imread
from Visuals import DrawInfoWindowImage, DrawInfoCloseWindow

class GSISetupNotice:
    def __init__(self):
        self.server_responded  = False
        self.was_window_closed = False
        self.img = imread('setup_notice.jpg')
        self.window_title = "Notice - Setup"
    
    def update(self, next_gamestate):
        if next_gamestate is None:
            return
        
        self.server_responded = True
    
    def getDrawInfo(self):
        if not self.server_responded:
            info = DrawInfoWindowImage()
            info.window_title = self.window_title
            info.img = self.img
            return info
        
        elif not self.was_window_closed: # Close notice window if not done yet
            info = DrawInfoCloseWindow()
            info.window_title = self.window_title
            self.was_window_closed = True
            print("[GSI Server] Running!")
            return info
