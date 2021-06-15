import sys
import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.append(os.path.join(BASE_DIR, 'low-level'))
sys.path.append(os.path.join(BASE_DIR, 'low-level/files/opt/seagate/sspl/setup/resource_map'))
