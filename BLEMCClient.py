'''*************************************************************************************

 Module
   BLEMCServer.py
 Revision
   1.0.1
 Description
   This module is meant for the user to implement the BLE_Class API
   in order to either issue commands to the motor directly through the REPL
   or to define sequences of motor commands
 Notes
 History
 When           Who     What/Why
 -------------- ---     --------
 6/25/20		WW      learn about Python and BLE

************************************************************************************'''

#available API Class functions:

# _e.client_write_speed(30) - input is int between 30 and 70 (rpm)
# _e.client_read_speed() - prints current speed to terminal
# speed characteristic initialized as 0

# _e.client_write_status(True) - turns on if True, off if False
# _e.client_read_status() - prints status of motor to terminal as 1/0 (on/off)
# status initialized to 0, set to one when motor rotates

# _e.client_write_direx(True) - input is True/False, depending on user circuit
# _e.client_read_direx() - reads direx as 1/0

# scripting interactions also useful, but you should comment out the lines in boot.py
# example script:

from BLE_Class import *
import utime

_e = mc_BLE()

gl_cmd_direction = True

def cmd_speed(spd=30):
	_e.client_write_speed(spd)

def cmd_status(sta=True):
	_e.client_write_status(sta)

def cmd_direx(drx=True):
	_e.client_write_direx(drx)

def switch_direx():
	global gl_cmd_direction
	if gl_cmd_direction:
		_e.client_write_direx(False)
		gl_cmd_direction = False
	else:
		_e.client_write_direx(True)
		gl_cmd_direction = True

def reset_server():
	_e.client_force_server_reset()

#delay of 50 ms generally works best between BLE write operations
def random_movement():
	_e.client_write_status(False)
	utime.sleep_ms(50)
	# _e.client_read_status()
	# utime.sleep_ms(50)
	_e.client_write_speed(70)
	utime.sleep_ms(50)
	# _e.client_read_speed()
	# utime.sleep_ms(50)
	_e.client_write_speed(30)
	utime.sleep_ms(50)
	_e.client_write_direx(False)
	utime.sleep_ms(50)
	# _e.client_read_direx()
	# utime.sleep_ms(50)
	_e.client_write_speed(43)
	utime.sleep_ms(50)
	_e.client_write_direx(True)
	utime.sleep_ms(50)
	_e.client_write_speed(30)
	utime.sleep_ms(50)
	_e.client_write_direx(False)
	utime.sleep_ms(50)
	_e.client_write_speed(70)
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









