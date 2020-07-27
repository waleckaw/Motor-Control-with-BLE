# import BLE/MC behavior package
import BLEMCServer as b

# disable default BLE prints
import esp
esp.osdebug(None)

# run BLE/MC behavior
b.coopSchedScript()
