import sys
import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.append(os.path.join(BASE_DIR, 'low-level'))
sys.path.append(os.path.join(BASE_DIR, 'low-level/solution/lr2'))
sys.path.append(os.path.join(BASE_DIR, 'low-level/solution/lr2/storage'))
sys.path.append(os.path.join(BASE_DIR, 'low-level/solution/lr2/server'))
