import threading

world = threading.local()
world._set = True