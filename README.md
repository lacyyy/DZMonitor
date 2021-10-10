# DZMonitor 1.0

A program that can display and announce useful information while playing CS:GO Danger Zone, such as:
- Danger Zone map rotation (display and/or audible announcer)

![Map Cycle Display](/unused/example_map_cycle.jpg)
- Personal redeployment cutoff / last chance to respawn (display and/or audible announcer)

![Personal Redeployment Cutoff Window](/unused/example_personal_redeployment_cutoff.jpg)

- Suicide Counter (display)

![Suicide Counter Window](/unused/example_suicide_counter.jpg)
- Flash sound player (plays sound whenever player gets flashed)

The windows with blue backgrounds can be used as transparent overlays in OBS:

![Transparent OBS Overlays](/unused/example_transparent_obs_overlays.jpg)

For optimal OBS filter settings, look into `personal_redeployment_cutoff/optimal_obs_filter_setting.jpg` and `suicide_counter/optimal_obs_filter_setting.jpg`.

## Is this a cheat? Will I get VAC-banned for using this?
No, this isn't a cheat and you won't get VAC-banned for using this. DZMonitor doesn't screw with the CS:GO program. Instead, it retrieves known game information like player health, kills, deaths, money, weapons, etc. through [Game State Integration](https://developer.valvesoftware.com/wiki/Counter-Strike:_Global_Offensive_Game_State_Integration) which is legit and provided by Valve itself.

## Reasons you shouldn't use DZMonitor
It should be noted what the [CS:GO Fair Play Guidelines](https://blog.counter-strike.net/index.php/fair-play-guidelines/) say about playing on official servers:

> Never use any automation for any reason.

DZMonitor merely displays/announces information the player could have deduced himself, it doesn't input anything into the game controls, like a cheat would. It could still be argued processing known game information and informing the player on his last chance to respawn is automation. You decide if DZMonitor violates the guidelines!
***Use at your own risk!***

Another obvious reason not to use DZMonitor: **You shouldn't download programs from strangers on the internet, possibly containing malware.** It would be best if someone you trust recommends DZMonitor. If you've got IT skills, you can check the source code for malicious content and compile it for yourself, completely making sure. That's why I published the source code along with the precompiled windows EXE.

# Download and Installation
1. Download DZMonitor for Windows 64bit TODO link
2. Extract the downloaded ZIP file
3. If CS:GO is open, close it. Then copy the `gamestate_integration_DZMonitor.cfg` file into the `cfg` folder of your CS:GO installation, e.g., `C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\csgo\cfg\`.
4. Now you can start DZMonitor by opening the `DZMonitor_vX.X.exe` file. Enjoy!

*Note: If you dislike any feature, you can individually disable it. See the section "Configuration" below.*

*Note: Selecting text inside the console causes program parts to halt. To deselect console text, press ESC.*

Currently I can only provide a download for Windows 64bit. MacOS and Linux users are required to run or compile the source code for themselves. Look at the sections below for instructions. Some IT and Python package installation skills are required!

## Donate
This took quite some effort and I'm glad a bunch of people showed interest in this tool! Since I decided to share it for free, donations are appreciated! If you've got any good ideas for more features, let me know :)
TODO donation link

## Configuration
You can individually enable/disable the following features:
  - `map_cycle_screen` (window that displays map cycle information)
  - `map_cycle_alerts` (audible announcer of map cycle information)
  - `personal_redeployment_cutoff_screen` (window that displays when your redeployments stop, only visible during match!)
  - `personal_redeployment_cutoff_alerts` (audible announcer of when your redeployments stop)
  - `flashed_sound` (plays sound whenever you get flashed)
  - `suicide_counter_screen` (window that displays the number of your suicides)

To do so, go into the corresponding `enable_<FEATURE_NAME>.txt` file and change the first line to a `1` to enable or a `0` to disable the feature. Save the file and restart DZMonitor.

***Furthermore, you can adjust the volume of each sound-playing feature.*** Look inside the folders for the `alert_volume.txt` or `sound_volume.txt` file!

***You can also change any image, sound or font file, as long as they keep their exact original name and file type!***
Lastly, there's a few more configurable things, each explained in their own `.txt` file. These include: Displayed text color, position and size. 

## Troubleshooting
> ***"Some features don't work"***

- Make sure you didn't halt the program by selecting text inside the console. To deselect console text, just press ESC.
- Make sure you copied the `gamestate_integration_DZMonitor.cfg` file into the `cfg` folder of your CS:GO installation and then ***restarted*** CS:GO.
- Make sure the desired feature is enabled in it's `enable_<FEATURE_NAME>.txt` file. If enabled, the console shows it in green text, in red when disabled.

> ***"The windows captured in OBS freeze and no longer update their information."***

- Make sure these windows aren't minimized.

## How to run from source
1. Install [Python](https://www.python.org) *v3.8* **(other version might not work)**
2. Install the following Python packages: **(other versions than listed here are not guaranteed to work)**
   - `pygame` *v2.0.1*
   - `opencv-python` *v4.5.3.56*
   - `numpy` *v1.21.1*
   - `Pillow` *v8.3.2*
   - `colorama` *v0.4.4*
3. Download the source repository
4. Inside the repository, run `python Main.py`

## How to compile from source
1. Complete steps 1, 2 and 3 from the preceding section "How to run from source"
2. Make sure your platform meets the [pyinstaller requirements](https://pyinstaller.readthedocs.io/en/stable/requirements.html)
3. Install [pyinstaller](https://pyinstaller.readthedocs.io/en/stable/installation.html)
5. Inside the repository, run `pyinstaller --onefile --icon icon.ico --name DZMonitor_vX.X Main.py`
6. The compiled binary is located under the subdirectory `dist/`, move it next to the `Main.py` file and run it
