# DZMonitor 1.0

## About
A program that displays and/or announces useful information while playing CS:GO Danger Zone, such as:
- Personal redeployment cutoff / last chance to respawn (announcer)
- Danger Zone map rotation (display and/or announcer)

![Map Cycle Display](/unused/example_map_cycle.jpg)

Additional functionalities that are less useful:
- Suicide Counter (display)
- Flash sound player (plays sound whenever player gets flashed)

## Is this a cheat? Will I get VAC-banned for using this?
No, this isn't a cheat and you won't get VAC-banned for using this. DZMonitor doesn't screw with the CS:GO program. Instead, it retrieves known game information like player health, kills, deaths, money, weapons, etc. through [Game State Integration](https://developer.valvesoftware.com/wiki/Counter-Strike:_Global_Offensive_Game_State_Integration) which is legit and provided by Valve itself.

## Reasons you shouldn't use DZMonitor
It should be noted what the [CS:GO Fair Play Guidelines](https://blog.counter-strike.net/index.php/fair-play-guidelines/) say about playing on official servers:

> Never use any automation for any reason.

DZMonitor merely displays/announces information the player could have deduced himself, it doesn't input anything into the game controls, like a cheat would. It could still be argued processing known game information and informing the player on his last chance to respawn is automation. You decide if DZMonitor violates the guidelines.

Another obvious reason not to use DZMonitor: **You shouldn't download programs from strangers on the internet, possibly containing malware.** It would be best if someone you trust recommends DZMonitor. If you've got IT skills, you can check the source code for malicious content and compile it for yourself, completely making sure. That's why I published the source code along with the precompiled windows EXE.

## Download
TODO link
Currently I can only provide a download for Windows 64bit. MacOS and Linux users are required to know how to compile the source code for themselves.

## Donate
This took quite some effort and I'm glad a bunch of people expressed interest in this tool! Since I decided to share it for free, donations are appreciated! If you've got any good ideas for more features, let me know :)
TODO donation link

## Configuration


## Troubleshooting


## How to compile from source
1. Install [Python](https://www.python.org) (v3.8.8 was used)
2. Install the following Python packages:
   - pygame (v2.0.1 was used)
   - opencv-python (v4.5.3.56 was used)
   - numpy (v1.21.1 was used)
   - Pillow (v8.3.2 was used)
   - colorama (v0.4.4 was used)
   - pyinstaller (v4.5 was used)
3. Run this inside the repository: `pyinstaller --onefile --icon icon.ico --name DZMonitor_vXX .\Main.py`
4. The compiled binary is located under "dist/", move it next to the "enable_X.txt"-files and run it
