import urllib.request
import util
import colorama
from colorama import Fore, Style

def isNewMapCycleAvailable(local_map_cycle_change_id_file_path):
    local_map_cycle_change_id = util.parseNumberFromFile(-1, local_map_cycle_change_id_file_path)
    if local_map_cycle_change_id == -1:
        print("[UpdateChecker] Can't check for map cycle updates: Can't get local change_id.txt")
        return False
    
    
    TARGET_URL = 'https://raw.githubusercontent.com/lacyyy/DZMonitor/main/map_cycle/change_id.txt'
    first_line = None
    try:
        for line in urllib.request.urlopen(TARGET_URL):
            first_line = line.decode('utf-8') #utf-8 or iso8859-1 or whatever the page encoding scheme is
            break # only need first line
    except Exception:
        print("[UpdateChecker] Failed to load map_cycle/change_id.txt from GitHub")
        return False
    if first_line is None:
        print("[UpdateChecker] Fail: map_cycle/change_id.txt from GitHub is empty!")
        return False
    remote_map_cycle_change_id = int(first_line)
    
    if remote_map_cycle_change_id > local_map_cycle_change_id:
        print('')
        print(Fore.MAGENTA, end='')
        print('---------------------------------------------------------------------------------------------')
        print('The map cycle changed! Download the updated DZMonitor at: https://github.com/lacyyy/DZMonitor')
        print('---------------------------------------------------------------------------------------------')
        print(Style.RESET_ALL, end='')
        print('')
        return True
    else:
        return False