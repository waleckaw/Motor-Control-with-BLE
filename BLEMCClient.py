# Client - BLE/Motor Control Proj
# Client lib automatically import as e. available methods to access motor include:

# e.client_writeSpeed(30) - input is int between 30 and 70 (rpm)
# e.client_readSpeed() - prints current speed to terminal
# speed characteristic initialized as 0

# e.client_writeStatus(True) - turns on if True, off if False
# e.client_readStatus() - prints status of motor to terminal as 1/0 (on/off)
# speed initialized to 0, set to one when motor rotates

# e.client_writeDirex(True) - input is True/False, depending on user circuit
# e.client_readDirex() - reads direx as 1/0

# example script:

e.client_writeStatus(False)
utime.sleep_ms(50)
e.client_writeSpeed(43)
utime.sleep_ms(50)
e.client_writeSpeed(30)
utime.sleep_ms(50)
e.client_writeDirex(False)
utime.sleep_ms(50)
e.client_writeSpeed(43)
utime.sleep_ms(50)
e.client_writeDirex(True)
utime.sleep_ms(50)
e.client_writeSpeed(30)
utime.sleep_ms(50)
e.client_writeDirex(False)
utime.sleep_ms(50)
e.client_writeSpeed(43)
utime.sleep_ms(50)
e.client_writeDirex(True)
utime.sleep_ms(50)
e.client_writeSpeed(30)		
utime.sleep_ms(50)
e.client_writeStatus(True)










