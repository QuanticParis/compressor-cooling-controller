# copy script from local folder to Pi
scp ~/Documents/Travail/Projects/Compressor-cooling-controller/github/compressor-cooling-controller/compressor-cooling-controller.py quantic@cryostat-raspberry:~/Desktop/

# code chantier
code chantier: 7523

# ssh to pi
ssh quantic@cryostat-raspberry

# dongle ip addresses
SYLVIA: 
192.168.0.2
eth1

BORIS:
192.168.1.2
eth2

-- configure dongles ---
sudo ip addr add 192.168.0.1/24 dev eth1
sudo ip link set eth1 up

sudo ip addr add 192.168.1.1/24 dev eth2
sudo ip link set eth2 up
----

go to VS code, select cryostat-raspberry

run python script: 

from gpiozero import Button, LED

PIN_VALVE_CONTROL = 1
output_valve_control = LED(PIN_VALVE_CONTROL)
output_valve_control.off()