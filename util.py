import cv2
import numpy as np
from colorama import Fore, Back, Style
error_list = []

def report_error(text):
    error_list.append(text)
    print(Fore.RED + "ERROR: " + text)
    print(Style.RESET_ALL, end='')

def parseNumberFromFile(default_value, path):
    try:
        with open(path) as f:
            text = f.readline()
            try:
                return float(text)
            except (ValueError, OverflowError):
                report_error("Number in " + str(path) + " couldn't be read. "
                                + str(default_value) + " is used instead.")
                return default_value
    except (FileNotFoundError, OSError):
        report_error("Couldn't open number file " + str(path) + ". "
                                + str(default_value) + " is used.")
        return default_value

def parseNumberListFromFile(default_value, path):
    try:
        with open(path) as f:
            num_list = []
            numbers = f.readline().split(',')
            for num_str in numbers:
                try:
                    num = float(num_str)
                    num_list.append(num)
                except (ValueError, OverflowError):
                    report_error("Number " + num_str + " in " + str(path) + " couldn't be read.")
            return num_list
    except (FileNotFoundError, OSError):
        report_error("Couldn't open number file " + str(path) + ". "
                                + str(default_value) + " is used.")
        return default_value

def overlay_transparent(background_rgb, overlay_rgba, x, y):
    x = int(x)
    y = int(y)
    
    background_width  = background_rgb.shape[1]
    background_height = background_rgb.shape[0]

    if x >= background_width or y >= background_height:
        return

    h, w = overlay_rgba.shape[0], overlay_rgba.shape[1]
    
    if x <= -w or y <= -h:
        return
    
    if x + w > background_width:
        w = background_width - x
        overlay_rgba = overlay_rgba[:, :w]
    if x < 0:
        overlay_rgba = overlay_rgba[:, -x:]
        w -= -x
        x = 0

    if y + h > background_height:
        h = background_height - y
        overlay_rgba = overlay_rgba[:h]
    if y < 0:
        overlay_rgba = overlay_rgba[-y:, :]
        h -= -y
        y = 0
    
    fg_mask = np.zeros((background_height, background_width, 4), dtype=np.uint8)
    fg_mask[y:y+h, x:x+w] = overlay_rgba
    
    # normalize alpha channels from 0-255 to 0-1
    alpha_foreground = fg_mask[:,:,3] / 255.0

    # set adjusted colors
    for color in range(0, 3):
        background_rgb[:,:,color] = alpha_foreground * fg_mask[:,:,color] + background_rgb[:,:,color] * (1 - alpha_foreground)