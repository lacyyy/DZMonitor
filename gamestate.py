import information
from operator import attrgetter

class GameState:
    def __init__(self, receive_time):
        self.receive_time = receive_time
        self.player = information.Player()
        self.map = information.Map()
        self.provider = information.Provider()
        self.phase_countdowns = information.PhaseCountdowns()
        self.bomb = information.Bomb()
        self.round = information.Round()
    
    def get(self, target, *argv):
        try:
            if len(argv) == 0:
                state = attrgetter(f"{target}")(self)
            elif len(argv) == 1:
                state = attrgetter(f"{target}.{argv[0]}")(self)
            elif len(argv) == 2:
                obj = attrgetter(f"{target}.{argv[0]}")(self)
                if hasattr(obj, "__getitem__"):
                    state = obj[f"{argv[1]}"]
                else:
                    state = None
            else:
                print("Too many arguments.")
                return False
            if "object" in str(state):
                return vars(state)
            else:
                return state
        except Exception as E:
            print(E)
            return False