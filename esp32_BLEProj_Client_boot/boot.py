# uncomment chunk below to directly use mc_BLE API commands like client_writeSpeed
# from BLE_Class import mc_BLE
# e=mc_BLE()

# uncomment line below if you want to write your own library (BLEMCClient.py) from 
# mc_BLE API and call its functions from the REPL or elsewhere
from BLEMCClient import *

# disable default BLE prints
import esp
esp.osdebug(None)