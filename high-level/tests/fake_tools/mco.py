#!/usr/bin/python
import sys

if len(sys.argv) > 3:

    if (sys.argv[1] == 'ping') and \
            (sys.argv[2] == '-F') and \
            (sys.argv[3] == 'role=storage'):
        print ('vmc-rekvm-ssu-1-5\ttime=25.32 ms')
        print ('vmc-rekvm-ssu-1-6\ttime=25.76 ms')
        print ('vmc-rekvm-ssu-1-1\ttime=26.12 ms')
        print ('vmc-rekvm-ssu-1-4\ttime=26.47 ms')
        print ('vmc-rekvm-ssu-1-3\ttime=26.84 ms')
        print ('vmc-rekvm-ssu-1-2\ttime=27.20 ms')
        print ('\n---- ping statistics ----')
        print ('6 replies max: 27.95 min: 24.68 avg: 26.54')
    elif (sys.argv[1] == 'find') and \
            (sys.argv[2] == '-F') and \
            (sys.argv[3] == 'role=storage'):
        print ('vmc-rekvm-ssu-1-2')
        print ('vmc-rekvm-ssu-1-1')
        print ('vmc-rekvm-ssu-1-6')
        print ('vmc-rekvm-ssu-1-3')
        print ('vmc-rekvm-ssu-1-5')
        print ('vmc-rekvm-ssu-1-4')
    elif (sys.argv[1] == 'rpc') and \
            (sys.argv[2] == 'runcmd') and \
            (sys.argv[3] == 'rc'):
        print ('vmc-rekvm-ssu-1-1')
        print ('Output : 0')
        print ('vmc-rekvm-ssu-1-2')
        print ('Output : 0')
        print ('vmc-rekvm-ssu-1-3')
        print ('Output : 0')
else:
    print
