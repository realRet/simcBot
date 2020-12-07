# simc-discord
SimulationCraft Bot for discord.

The following things are needed to run the bot:
* Python 3.9+
* Flask 1.1.2+: https://flask.palletsprojects.com/en/1.1.x/
* Python Discord lib: https://github.com/Rapptz/discord.py
* Webservice on the server to hand out a link to the finished simulation.
* A working version of simulationcraft TCI


***Help for simulation through Discord:***

**Options:**
```
-c      -character          **in-game name**
-r      -realm              **realm name** *(Default is Magtheridon)*
-f      -fightstyle         **Choose between different fightstyles - Options: Patchwerk, LightMovement, HeavyMovement, HecticAddCleave, HelterSkelter**
-l      -length             **Choose fight length in seconds** *(Default is 400)*
-v      -version             **Gives the version of simulationcraft being used**
```

-> Simulate you character using:
`!simc -character NAME`

The bot will whisper with a unique link where you need to paste your addon data.
Addon can be found here: <https://mods.curse.com/addons/wow/simulationcraft>

__Example__:
```
# Zuhlarz - Elemental - 2020-12-07 17:55 - EU/Draenor
# SimC Addon 9.0.2-10
# Requires SimulationCraft 901-01 or newer

shaman="Zuhlarz"
level=60
race=troll
region=eu
server=draenor
role=spell
professions=herbalism=150/mining=150
talents=2311122
spec=elemental

covenant=necrolord
# soulbind=plague_deviser_marileth:4,323074/147:4/323091
soulbind=emeni:5,342156/118:4/323921
# conduits_available=100:4/102:2/103:4/104:2/110:4/112:3/117:4/118:4/147:4/95:3/97:4/93:1
# renown=6

head=,id=178738,bonus_id=6807/6652/7193/1498/6646
neck=,id=178707,bonus_id=6807/6652/7193/1498/6646
shoulder=,id=178733,bonus_id=6806/6652/1485/4785
back=,id=180123,bonus_id=6807/6652/1498/6646
chest=,id=178815,bonus_id=6807/6652/1498/6646
tabard=,id=69210
wrist=,id=178703,bonus_id=6807/6652/7193/1498/6646
hands=,id=178798,enchant_id=6205,bonus_id=6807/6652/1498/6646
waist=,id=180110,bonus_id=6807/6652/7193/1498/6646
legs=,id=178839,bonus_id=6806/42/1485/4785
feet=,id=178830,bonus_id=6805/6652/1472/4785
finger1=,id=178848,bonus_id=6807/6652/6935/1498/6646
finger2=,id=178781,bonus_id=6807/6652/7194/1498/6646
trinket1=,id=178783,bonus_id=6807/6652/1498/6646
trinket2=,id=178810,bonus_id=6807/6652/1498/6646
main_hand=,id=178789,bonus_id=6807/6652/1498/6646
off_hand=,id=178712,bonus_id=6807/6652/1498/6646
```
