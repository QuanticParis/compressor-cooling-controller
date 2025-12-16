# copy script from local folder to Pi
scp ~/Documents/Travail/Projects/Compressor-cooling-controller/github/compressor-cooling-controller/compressor-cooling-controller.py quantic@cryostat-raspberry:~/Desktop/

# donner la clé à influxdb:

Sur la raspberry copier le fichier `.env.dist` dans `.env` (`cp .env.dist .env`) et mettre le token influx dedans.
**Attention: le token est un secret et doit être traité comme un mot de passe, ne pas le mettre dans git !**

# code chantier
code chantier: 7523

# ssh to pi
ssh quantic@cryostat-raspberry

# run script in background
nohup python compressor-cooling-controller.py > myscript.log 2>&1 &

# check process is running
ps aux | grep compressor-cooling-controller.py

# kill process ?
pkill -f compressor-cooling-controller.py

# dongle ip addresses
SYLVIA: 
192.168.0.2
eth1

BORIS:
192.168.1.2
eth2

# configure dongles 

```
sudo ip addr add 192.168.0.1/24 dev eth1
sudo ip link set eth1 up

sudo ip addr add 192.168.1.1/24 dev eth2
sudo ip link set eth2 up
```