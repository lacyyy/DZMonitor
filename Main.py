import sys
import traceback
import time
import json
#import logging
from os.path import join
from queue import Empty as QEmpty

from Visuals            import Visuals
from SoundPlayer        import SoundPlayer
from AlertAnnouncer     import AlertAnnouncer
from GSISetupNotice     import GSISetupNotice
from MapCycle           import MapCycle
from RedeploymentCutoff import RedeploymentCutoff
from FlashedSound       import FlashedSound
from SuicideCounter     import SuicideCounter

from MapCycleUpdateChecker import isNewMapCycleAvailable
import gamestate
from server import GSIServer
import colorama
from colorama import Fore, Style
from cv2 import imread
from Visuals import DrawInfoWindowImage

import util
import Constants

def mainFunc():
    try:
        colorama.init()
        print(Fore.CYAN + '==== DZMonitor ' + str(Constants.VERSION) + ' ====')
        print(Style.RESET_ALL, end='')
        
        print("")
        print(Fore.YELLOW + 'CAUTION - Do not select text in this console window - this unnoticeably pauses the program!')
        print('If you selected something, just press ESC.')
        print('Minimizing the regularly updated windows will freeze them in OBS.')
        print(Style.RESET_ALL, end='')
        print("")
    
        #logging.basicConfig(filename='last_session.log',level=logging.DEBUG)
        
        # load configurations
        enable_map_cycle_screen       = 0 != util.parseNumberFromFile(1, 'enable_map_cycle_screen.txt')
        enable_map_cycle_alerts       = 0 != util.parseNumberFromFile(1, 'enable_map_cycle_alerts.txt')
        enable_per_red_cutoff_screen  = 0 != util.parseNumberFromFile(1, 'enable_personal_redeployment_cutoff_screen.txt')
        enable_per_red_cutoff_alerts  = 0 != util.parseNumberFromFile(1, 'enable_personal_redeployment_cutoff_alerts.txt')
        enable_flashed_sound          = 0 != util.parseNumberFromFile(1, 'enable_flashed_sound.txt')
        enable_suicide_counter_screen = 0 != util.parseNumberFromFile(1, 'enable_suicide_counter_screen.txt')
        
        print('Enabled features:')
        print('')
        print(Fore.GREEN, end='')
        if enable_map_cycle_screen:
            print('  - map_cycle_screen')
        if enable_map_cycle_alerts:
            print('  - map_cycle_alerts')
        if enable_per_red_cutoff_screen:
            print('  - personal_redeployment_cutoff_screen')
        if enable_per_red_cutoff_alerts:
            print('  - personal_redeployment_cutoff_alerts')
        if enable_flashed_sound:
            print('  - flashed_sound')
        if enable_suicide_counter_screen:
            print('  - suicide_counter_screen')
        print(Style.RESET_ALL, end='')
        print('')
        
        
        print('Disabled features:')
        print('')
        print(Fore.RED, end='')
        if not enable_map_cycle_screen:
            print('  - map_cycle_screen')
        if not enable_map_cycle_alerts:
            print('  - map_cycle_alerts')
        if not enable_per_red_cutoff_screen:
            print('  - personal_redeployment_cutoff_screen')
        if not enable_per_red_cutoff_alerts:
            print('  - personal_redeployment_cutoff_alerts')
        if not enable_flashed_sound:
            print('  - flashed_sound')
        if not enable_suicide_counter_screen:
            print('  - suicide_counter_screen')
        print(Style.RESET_ALL, end='')
        print('')
        
        # graphics thread object
        visuals = Visuals(Constants.VISUALS_FPS)
        
        # helpers
        sound_player    = SoundPlayer()
        alert_announcer = AlertAnnouncer('alert_announcer/', sound_player)
        
        # modules
        map_cycle       = MapCycle          ('map_cycle/', alert_announcer, enable_map_cycle_alerts)
        redep_cutoff    = RedeploymentCutoff('personal_redeployment_cutoff/', alert_announcer, enable_per_red_cutoff_alerts, enable_per_red_cutoff_screen)
        flashed_sound   = FlashedSound      ('flashed_sound/', sound_player, enable_flashed_sound)
        suicide_counter = SuicideCounter    ('suicide_counter/')
        
        # game state integration server
        server = GSIServer(("127.0.0.1", 3000), "602HJ031ONM12FT1K007WQYO1W2W1JBB")
        server.start_server()
        gsi_setup_notice = GSISetupNotice()
        
        # check for map cycle updates on github
        if isNewMapCycleAvailable('map_cycle/change_id.txt'):
            img = imread('map_cycle/map_cycle_update_notice.jpg')
            if img is not None:
                draw_info = DrawInfoWindowImage()
                draw_info.window_title = "Notice - Map Cycle Update"
                draw_info.img = img
                visuals.update(draw_info)
        
        def update_modules(gamestate):
            gsi_setup_notice.update(gamestate)
            redep_cutoff    .update(gamestate)
            map_cycle       .update(gamestate)
            flashed_sound   .update(gamestate)
            suicide_counter .update(gamestate)
        
        def update_visuals():
            visuals.update(gsi_setup_notice.getDrawInfo())
            
            if enable_map_cycle_screen:
                visuals.update(map_cycle.getDrawInfo())
            
            if enable_per_red_cutoff_screen:
                visuals.update(redep_cutoff.getDrawInfo())
            
            if enable_suicide_counter_screen:
                visuals.update(suicide_counter.getDrawInfo())
            
        
        # if gamestate didn't change for too long, update again with previous one
        MIN_GAMESTATE_UPDATE_RATE = 8
        prev_update_time = None
        prev_gamestate = None
        
        visual_update_required = False
        running = True
        while running:
            
            if visuals.getReceivedKeyPress() is not None:
                running = False
                break
            
            # Process all available new gamestates
            new_gamestate_count = 0
            while server.gamestate_q.qsize() > 0:
                try:
                    next_item = server.gamestate_q.get_nowait()
                    payload_time = next_item[0]
                    payload_body = next_item[1]
                    
                    payload = json.loads(payload_body)
                    
                    #logging.debug('NEW JSON: %s', str(payload))
                    
                    #if self.server.prev_payload is not None:
                    #    if payload == self.server.prev_payload:
                    #        return
                    #self.server.prev_payload = payload
                    
                    if not server.authenticate_payload(payload):
                        print("auth_token does not match.")
                        continue
                    
                    new_gamestate_count += 1
                    
                    #print("----- New JSON -----")
                    #print(payload_body)
                    #print("json count:", new_gamestate_count)
                    
                    next_gamestate = gamestate.GameState(payload_time)
                    server.parser.parse_payload(payload, next_gamestate)
                    
                    prev_update_time = time.perf_counter()
                    update_modules(next_gamestate)
                    visual_update_required = True
                    
                    prev_gamestate = next_gamestate
                except QEmpty:
                    break
            
            # If last update was too long ago, force update
            if (prev_update_time is None or
                    time.perf_counter() - prev_update_time >= (1 / MIN_GAMESTATE_UPDATE_RATE)):
                prev_update_time = time.perf_counter()
                update_modules(None)#prev_gamestate)
                visual_update_required = True
            elif new_gamestate_count == 0:
                time.sleep(0.001)
            
            # Update visual data
            if visual_update_required:
                update_visuals()
                visual_update_required = False
        
    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc(file=sys.stdout)
    finally:
        if 'visuals' in locals():
            visuals.cleanup()
        if 'server' in locals():
            print('[GSI Server] Shutting down...')
            server.shutdown()
        if 'sound_player' in locals():
            sound_player.cleanup()
            
        colorama.deinit()
        
        print(".")
        print(".")
        print(".")
        try:
            input("Program terminated. You can close this window now.")
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    mainFunc()
