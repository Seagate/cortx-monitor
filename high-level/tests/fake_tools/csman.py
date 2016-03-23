#!/usr/bin/python
import sys

if len(sys.argv) > 3:
    if (sys.argv[1] == 'service') and \
            (sys.argv[2] == 'notifications') and \
            (sys.argv[3] == 'show'):
        print ('No current outstanding service call events.')
    else:
        print
else:
    print
