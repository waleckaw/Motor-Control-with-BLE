# Client - BLE/Motor Control Proj
# Client lib automatically import as e to use from REPL. 

#available methods to access motor include:

# _e.client_write_speed(30) - input is int between 30 and 70 (rpm)
# _e.client_read_speed() - prints current speed to terminal
# speed characteristic initialized as 0

# _e.client_write_status(True) - turns on if True, off if False
# _e.client_read_status() - prints status of motor to terminal as 1/0 (on/off)
# speed initialized to 0, set to one when motor rotates

# _e.client_write_direx(True) - input is True/False, depending on user circuit
# _e.client_read_direx() - reads direx as 1/0

# scripting interactions also useful, but you should comment out the lines in boot.py
# example script:

from BLE_Class import *
import utime

_e = mc_BLE()

def random_func():
	_e.client_write_status(False)
	utime.sleep_ms(50)
	_e.client_read_status()
	utime.sleep_ms(50)
	_e.client_write_speed(43)
	utime.sleep_ms(50)
	_e.client_read_speed()
	utime.sleep_ms(50)
	_e.client_write_speed(30)
	utime.sleep_ms(50)
	_e.client_write_direx(False)
	utime.sleep_ms(50)
	_e.client_read_direx()
	utime.sleep_ms(50)
	_e.client_write_speed(43)
	utime.sleep_ms(50)
	_e.client_write_direx(True)
	utime.sleep_ms(50)
	_e.client_write_speed(30)
	utime.sleep_ms(50)
	_e.client_write_direx(False)
	utime.sleep_ms(50)
	_e.client_write_speed(43)
	utime.sleep_ms(50)
	_e.client_write_direx(True)
	utime.sleep_ms(50)
	_e.client_write_speed(30)		
	utime.sleep_ms(50)
	_e.client_write_status(True)

def do_more_stuff():
	_e.client_write_status(False)
	utime.sleep_ms(50)
	_e.client_write_direx(True)
	utime.sleep_ms(50)
	_e.client_write_speed(30)
	utime.sleep_ms(50)
	_e.client_write_direx(False)
	utime.sleep_ms(50)
	_e.client_write_status(True)

def stop():
	_e.client_write_status(False)









