# ssh to pi
ssh quantic@129.199.115.236
pwd: the mother of all instruments

# acticate controller environment
source ~/venvs/controller/bin/activate

# run script in background
nohup python compressor-cooling-controller.py > myscript.log 2>&1 &

# check process is running
ps aux | grep compressor-cooling-controller.py

# kill process ?
pkill -f compressor-cooling-controller.py

# configure dongles 

```
sudo ip addr add 192.168.0.1/24 dev eth1
sudo ip link set eth1 up

sudo ip addr add 192.168.1.1/24 dev eth2
sudo ip link set eth2 up
```

# copy script from local to Pi
scp ~/Documents/Travail/Projects/Compressor-cooling-controller/github/compressor-cooling-controller/compressor-cooling-controller.py quantic@cryostat-raspberry:~/Desktop/

# copy script from Pi to local
scp quantic@cryostat-raspberry:~/Desktop/compressor-cooling-controller.py ~/Documents/Travail/Projects/Compressor-cooling-controller/github/compressor-cooling-controller/

# donner la clé à influxdb:

Sur la raspberry copier le fichier `.env.dist` dans `.env` (`cp .env.dist .env`) et mettre le token influx dedans.
**Attention: le token est un secret et doit être traité comme un mot de passe, ne pas le mettre dans git !**

# code chantier
code chantier: 7523