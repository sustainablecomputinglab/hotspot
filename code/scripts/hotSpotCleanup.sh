#!/bin/bash

rm -rf /home/ubuntu/hotSpot/snapshot
echo $(date) "Beginning hotSpotLXC checkpointing" >> /home/ubuntu/hotSpot/system.log
lxc-checkpoint -s -n hotSpotLXC -v -D /home/ubuntu/hotSpot/snapshot/
echo $(date) "Completed checkpointing" >> /home/ubuntu/hotSpot/system.log

cp -f /etc/network/interfaces.d/br0.cfg /var/lib/lxc/
cp -f /home/ubuntu/.aws/credentials /var/lib/lxc/
cp -fR /home/ubuntu/hotSpot /var/lib/lxc/
umount /dev/xvdh

# configure eth1 and br0 with the actual MAC address
ifconfig eth1 down
ifconfig eth1 hw ether 06:79:b3:6b:40:77
ifconfig br0 hw ether 06:79:b3:6b:40:77
ifconfig eth1 up
ifdown br0
