#!/usr/bin/env bash

# Change the permissions of he script in sspl-hl.spec file
if [ $1 = "poweron" ]
then
    echo discovering kvm nodes
    echo qemu+tcp://192.168.0.1:16509/system
    echo Nodes with role storage:
    echo vmc-rekvm-castor-kvm001-05
    echo vmc-rekvm-castor-kvm001-04
    echo vmc-rekvm-castor-kvm001-03
    echo vmc-rekvm-castor-kvm001-06
    echo vmc-rekvm-castor-kvm001-02
    echo vmc-rekvm-castor-kvm001-01
    echo It took 8 seconds to complete this task...
elif [ $1 = "poweroff" ]
then
    echo qemu+tcp://192.168.0.1:16509/system
    echo Nodes with role storage:
    echo vmc-rekvm-castor-kvm001-05
    echo vmc-rekvm-castor-kvm001-04
    echo vmc-rekvm-castor-kvm001-03
    echo vmc-rekvm-castor-kvm001-06
    echo vmc-rekvm-castor-kvm001-02
    echo vmc-rekvm-castor-kvm001-01
    echo It took 8 seconds to complete this task...
elif [ $1 = "status" ]
then
    echo 172.16.2.101
    echo Chassis Power is on
    echo 172.16.2.102
    echo Chassis Power is on
    echo 172.16.2.103
    echo Chassis Power is on
    echo 172.16.2.104
    echo Chassis Power is on
    echo It took 24 seconds to complete this task...
fi