#Server - BLE/Motor Control Proj

import machine
from machine import Pin
from machine import Timer

from WWsched import coopSched
from WWsched import flag

from MC_Class import MC
from BLE_Class import mc_BLE

from BLE_Class import BLE_ATTR_STATUS
from BLE_Class import BLE_ATTR_SPEED
from BLE_Class import BLE_ATTR_DIREX
from BLE_Class import BLE_ATTR_RESET

from micropython import const

# toggle debug print statements
_WW_DEBUG = const(0)

# Motor Controller Constants
_TASKID_MCTASK =const(0)
# Motor Controller states
_MCSTATE_IDLE = const(1)
_MCSTATE_RUNNING = const(2)
_MCSTATE_SPEEDINGUP = const(3)
_MCSTATE_SLOWINGDOWN = const(4)
_MCSTATE_MOTOROFF = const(5)
# Motor Controller cmd types
_STATUS_CMD = const(0)
_SPEED_CMD = const(1)
_DIREX_CMD = const(2)
# Motor Controller achieve speed buffer
_SPEED_THRESHOLD_BUF = const(3)

# esp32 Constants
_TASKID_BLETASK =const(1)
# esp32 BLE states
_BLESTATE_NOTCONNECTED = const(1)
_BLESTATE_CONNECTED = const(2)

# flags ID's are shared between tasks
_FLAG_BLE_CONNECTED = const(0)
_FLAG_UPDATE_STATUS = const(1)
_FLAG_UPDATE_SPEED = const(2)
_FLAG_UPDATE_DIREX = const(3)

MC_SPEED_RANGE = [30, 70]

# instance of scheduler used in startup script
scheduler = coopSched(tick_per_ms=30, use_esp32=True) #per = period, not /

# task in charge of motor operation
class MCTask:

	# intialize MCTask - attributes include state, MC() obj from MC_Class.py, flags, and others
	def __init__(self):
		self._task_ID = _TASKID_MCTASK
		self._state = _MCSTATE_IDLE
		self._last_state = _MCSTATE_IDLE
		self._mc = MC()
		update_desired_speed_flag = flag(fn=self._update_speed, ftype=_FLAG_UPDATE_SPEED, take_param=True)
		BLE_connection_flag = flag(fn=self._set_to_running, ftype=_FLAG_BLE_CONNECTED)
		update_status_flag = flag(fn=self._update_status, ftype=_FLAG_UPDATE_STATUS, take_param=True)
		update_direx_flag = flag(fn=self._update_direx, ftype=_FLAG_UPDATE_DIREX, take_param=True)
		#order of flags in flag_list should follow order of flag enumeration
		self._flag_list = [BLE_connection_flag, update_status_flag, update_desired_speed_flag, update_direx_flag]
		self._cmd_list = []
		self.direx = 1

	# cmd's are enqueued for MCTask to act on when ready
	class cmd:
		def __init__(self, type_=None, input_=0):
			self._type = type_
			self._input = input_

	# all tasks added to an instance of WWsched must have a function called run 
	#MCtask operation - handles connection to server and other commands to the motor. 
	#allows user to enqueue commands while motor is off or if it has not reached 
	# previous desired speed
	def _run(self):
		if _WW_DEBUG: print('running MCTask, state = ', self._state)
		if _WW_DEBUG: print('cmd_queue =', self._cmd_list)
		# task initial state - wait to take action until connected
		if self._state == _MCSTATE_IDLE: 
			return
		# check if motor has reached target speed
		if self._state == _MCSTATE_SPEEDINGUP and self._mc.speed > (self._mc._target_speed - _SPEED_THRESHOLD_BUF):
			self._state = _MCSTATE_RUNNING
		elif self._state == _MCSTATE_SLOWINGDOWN and self._mc.speed < (self._mc._target_speed + _SPEED_THRESHOLD_BUF):
			self._state = _MCSTATE_RUNNING
		if not self._cmd_list:
			return
		else:
			if self._state == _MCSTATE_SPEEDINGUP:
				if self._cmd_list[0]._type != _SPEED_CMD:
					new_cmd = self._cmd_list.pop(0)
					if new_cmd._type == _STATUS_CMD:
						self._mc.toggle()
						self._last_state = self._state
						self._state = _MCSTATE_MOTOROFF
					elif new_cmd._type == _DIREX_CMD:
						# direction changes but speed still increases up to target
						if self.direx != 0 and new_cmd._input == 0:
							self._mc.change_direx()
							self.direx = 0
						elif self.direx == 0 and new_cmd._input != 0:
							self._mc.change_direx()
							self.direx = 1

			elif self._state == _MCSTATE_SLOWINGDOWN:
				if self._cmd_list[0]._type != _SPEED_CMD:
					new_cmd = self._cmd_list.pop(0)
					if new_cmd._type == _STATUS_CMD:
						self._mc.toggle()
						self._last_state = self._state
						self._state = _MCSTATE_MOTOROFF
					elif new_cmd._type == _DIREX_CMD:
						# direction changes but speed still decreases up to target
						if self.direx != 0 and new_cmd._input == 0:
							self._mc.change_direx()
							self.direx = 0
						elif self.direx == 0 and new_cmd._input != 0:
							self._mc.change_direx()
							self.direx = 1

			# running, so motor will now reply to speed cmds
			elif self._state == _MCSTATE_RUNNING:
				new_cmd = self._cmd_list.pop(0)
				if new_cmd._type == _STATUS_CMD:
					if not new_cmd._input:
						self._mc.toggle()
						self._last_state = self._state
						self._state = _MCSTATE_MOTOROFF
					else:
						if _WW_DEBUG: print('motor already on')
				elif new_cmd._type == _SPEED_CMD:
					if new_cmd._input > self._mc.speed:
						self._state = _MCSTATE_SPEEDINGUP
					else:
						self._state = _MCSTATE_SLOWINGDOWN
					self._mc.use_control(use=True, speed=new_cmd._input)
				elif new_cmd._type == _DIREX_CMD:
					if self.direx != 0 and new_cmd._input == 0:
						self._mc.change_direx()
						self.direx = 0
					elif self.direx == 0 and new_cmd._input != 0:
						self._mc.change_direx()
						self.direx = 1

			# off, so motor will enqueue commands until status-on command is received and then it
			# will resume operation and respond to all available commands in queue
			elif self._state == _MCSTATE_MOTOROFF:
				new_cmd = self._cmd_list[0]
				if new_cmd._type == _STATUS_CMD:
					if new_cmd._input:
						self._mc.toggle()
						self._state = self._last_state
					else:
						if _WW_DEBUG: print('motor already off')
					del self._cmd_list[0]
				else:
					# if there is a command to turn it back on that is not in front, fast forward it to the front
					try:
						cmd_to_remove = next(a for a in self._cmd_list if a._type == _STATUS_CMD and a._input > 0)
					except StopIteration:
						cmd_to_remove = None
					if cmd_to_remove is not None:
						self._cmd_list.remove(cmd_to_remove)
						self._mc.toggle()
						self._state = self._last_state

	# callback function for speed update flag that puts motor speed command in queue 
	def _update_speed(self, desired_speed=0):
		if _WW_DEBUG: print('_update_speed being called. desired_speed = ', desired_speed)
		if desired_speed >= MC_SPEED_RANGE[0] and desired_speed <= MC_SPEED_RANGE[1]:
			new_spd_cmd = MCTask.cmd(_SPEED_CMD, desired_speed)
			self._cmd_list.append(new_spd_cmd)
			if _WW_DEBUG: print('cmd_list: ', self._cmd_list)
		else:
			if _WW_DEBUG: print('desired speed not passed in, must be between 30 and 70')

	# callback function for status update flag that puts motor ON/OFF command in queue 
	def _update_status(self, desired_status):
		if _WW_DEBUG: print('calling _update_status')
		new_status_cmd = MCTask.cmd(_STATUS_CMD, desired_status)
		self._cmd_list.append(new_status_cmd)

	# callback function for direction update flag that puts motor direction command in queue
	def _update_direx(self, desired_direx):
		if _WW_DEBUG: print('calling _update_direx')
		new_direx_cmd = MCTask.cmd(_DIREX_CMD, desired_direx)
		self._cmd_list.append(new_direx_cmd)

	# callback function for connect flag that sets task active once BLE connection is made
	def _set_to_running(self):
		self._state = _MCSTATE_RUNNING

class BLETask:

	# initialize BLETask - attributes inlcude state, flags, mc_BLE from BLE_Class
	def __init__(self):
		self._state = _BLESTATE_NOTCONNECTED
		self._task_ID = _TASKID_BLETASK
		update_desired_speed_flag = flag(fn=self._dummy_method, ftype=_FLAG_UPDATE_SPEED)
		BLE_connection_flag = flag(fn=None, ftype=_FLAG_BLE_CONNECTED)
		update_status_flag = flag(fn=None, ftype=_FLAG_UPDATE_STATUS)
		update_direx_flag = flag(fn=None, ftype=_FLAG_UPDATE_DIREX)
		#order of flags in flag_list must follow order of flag enumeration, so that flags can be set using flag ID's
		self._flag_list = [BLE_connection_flag, update_status_flag, update_desired_speed_flag, update_direx_flag]
		self._ble = mc_BLE(server_role=True)
		self._ble.server_init_direx()


	# all tasks added must have a function called run
	# BLETask operation - checks for connection to switch to connected state, then checks for BLE attribute updates
	# (writes from client) and posts appropriate flag to be operated on by MCTask
	def _run(self):
		if _WW_DEBUG: print('running BLETask')
		if self._state == _BLESTATE_NOTCONNECTED:
			if self._ble.cli_serv_get_connection_status():
				self._state = _BLESTATE_CONNECTED
				if _WW_DEBUG: print('connection!!! in BLETask run')
				self._flag_list[BLE_ATTR_STATUS].set_flag()
		# check if an attribute has been written by client, then post command to MC_Task
		if (self._state == _BLESTATE_CONNECTED):
			if self._ble._update_ready:
				# status (ON/OFF)
				if self._ble._attr_update_dict[BLE_ATTR_STATUS]:
					des_status = self._ble.server_read_motor_characteristic(BLE_ATTR_STATUS)
					self._flag_list[_FLAG_UPDATE_STATUS].set_flag(inp_param=des_status)
					self._ble._attr_update_dict[BLE_ATTR_STATUS] = 0 # unset update indicator
				#speed
				if self._ble._attr_update_dict[BLE_ATTR_SPEED]:
					des_speed = self._ble.server_read_motor_characteristic(BLE_ATTR_SPEED)
					self._flag_list[_FLAG_UPDATE_SPEED].set_flag(inp_param=des_speed)
					self._ble._attr_update_dict[BLE_ATTR_SPEED] = 0
				#direx
				if self._ble._attr_update_dict[BLE_ATTR_DIREX]:
					des_direx = self._ble.server_read_motor_characteristic(BLE_ATTR_DIREX)
					self._flag_list[_FLAG_UPDATE_DIREX].set_flag(inp_param=des_direx)
					self._ble._attr_update_dict[BLE_ATTR_DIREX] = 0
				self._ble._update_ready = False
				#reset
				if self._ble._attr_update_dict[BLE_ATTR_RESET]:
					if _WW_DEBUG: print('calling reset')
					machine.reset()

	def _dummy_method(self):
		pass

# function called in Server boot that initializes and sets off entire system
def coopSchedScript():
	mt = MCTask()
	bt = BLETask()
	# task intervals must be higher than sys tick interval
	scheduler.add_task(mt, 180) #30
	scheduler.add_task(bt, 60) #30
	scheduler.run()

















