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

#Toggle debug print statements
WW_DEBUG = const(0)

# Motor Controller Constants
TASKID_MCTASK =const(0)
# Motor Controller states
MCSTATE_IDLE = const(1)
MCSTATE_RUNNING = const(2)
MCSTATE_SPEEDINGUP = const(3)
MCSTATE_SLOWINGDOWN = const(4)
MCSTATE_MOTOROFF = const(5)
# Motor Controller cmd types
STATUS_CMD = const(0)
SPEED_CMD = const(1)
DIREX_CMD = const(2)
# Motor Controller achieve speed buffer
SPEED_THRESHOLD_BUF = const(3)

# esp32 Constants
TASKID_BLETASK =const(1)
# esp32 BLE states
BLESTATE_NOTCONNECTED = const(1)
BLESTATE_CONNECTED = const(2)

# flags ID's are shared between tasks
FLAG_BLE_CONNECTED = const(0)
FLAG_UPDATE_STATUS = const(1)
FLAG_UPDATE_SPEED = const(2)
FLAG_UPDATE_DIREX = const(3)

MC_Speed_Range = [30, 70]

# instance of scheduler used in startup script
scheduler = coopSched(tick_per_ms=30, use_esp32=True) #per = period, not /

# task in charge of motor operation
class MCTask:

	# intialize MCTask - attributes include state, MC() obj from MC_Class.py, flags, and others
	def __init__(self):
		self.task_id = TASKID_MCTASK
		self.state = MCSTATE_IDLE
		self.last_state = MCSTATE_IDLE
		self.mc = MC()
		BLE_Updated_Desired_Speed_Flag = flag(fn=self.updateSpeed, ftype=FLAG_UPDATE_SPEED, take_param=True)
		BLE_Connected_Flag = flag(fn=self.setToRunning, ftype=FLAG_BLE_CONNECTED)
		Update_Status_Flag = flag(fn=self.updateStatus, ftype=FLAG_UPDATE_STATUS, take_param=True)
		Update_Direx_Flag = flag(fn=self.updateDirex, ftype=FLAG_UPDATE_DIREX, take_param=True)
		#order of flags in flag_list should follow order of flag enumeration
		self.flag_list = [BLE_Connected_Flag, Update_Status_Flag, BLE_Updated_Desired_Speed_Flag, Update_Direx_Flag]
		self.cmd_list = []
		self.direx = 1

	# cmd's are enqueued for MCTask to act on when ready
	class cmd:
		def __init__(self, type, input=0):
			self._type = type
			self._input = input

	# all tasks added to an instance of WWsched must have a function called run 
	#MCtask operation - handles connection to server and other commands to the motor. 
	#allows user to enqueue commands while motor is off or if it has not reached 
	# previous desired speed
	def run(self):
		if WW_DEBUG: print('running MCTask, state = ', self.state);
		if WW_DEBUG: print('cmd_queue =', self.cmd_list)
		# task initial state - wait to take action until connected
		if self.state == MCSTATE_IDLE: 
			return
		# check if motor has reached target speed
		if self.state == MCSTATE_SPEEDINGUP and self.mc.speed > (self.mc.target_speed - SPEED_THRESHOLD_BUF):
			self.state = MCSTATE_RUNNING
		elif self.state == MCSTATE_SLOWINGDOWN and self.mc.speed < (self.mc.target_speed + SPEED_THRESHOLD_BUF):
			self.state = MCSTATE_RUNNING
		if not self.cmd_list:
			return
		else:
			if self.state == MCSTATE_SPEEDINGUP:
				if self.cmd_list[0]._type != SPEED_CMD:
					new_cmd = self.cmd_list.pop(0)
					if new_cmd._type == STATUS_CMD:
						self.mc.toggle()
						self.last_state = self.state
						self.state = MCSTATE_MOTOROFF
					elif new_cmd._type == DIREX_CMD:
						# direction changes but speed still increases up to target
						if self.direx != 0 and new_cmd._input == 0:
							self.mc.changeDirex()
							self.direx = 0
						elif self.direx == 0 and new_cmd._input != 0:
							self.mc.changeDirex()
							self.direx = 1

			elif self.state == MCSTATE_SLOWINGDOWN:
				if self.cmd_list[0]._type != SPEED_CMD:
					new_cmd = self.cmd_list.pop(0)
					if new_cmd._type == STATUS_CMD:
						self.mc.toggle()
						self.last_state = self.state
						self.state = MCSTATE_MOTOROFF
					elif new_cmd._type == DIREX_CMD:
						# direction changes but speed still decreases up to target
						if self.direx != 0 and new_cmd._input == 0:
							self.mc.changeDirex()
							self.direx = 0
						elif self.direx == 0 and new_cmd._input != 0:
							self.mc.changeDirex()
							self.direx = 1

			# running, so motor will now reply to speed cmds
			elif self.state == MCSTATE_RUNNING:
				new_cmd = self.cmd_list.pop(0)
				if new_cmd._type == STATUS_CMD:
					if not new_cmd._input:
						self.mc.toggle()
						self.last_state = self.state
						self.state = MCSTATE_MOTOROFF
					else:
						if WW_DEBUG: print('motor already on')
				elif new_cmd._type == SPEED_CMD:
					if new_cmd._input > self.mc.speed:
						self.state = MCSTATE_SPEEDINGUP
					else:
						self.state = MCSTATE_SLOWINGDOWN
					self.mc.useControl(use=True, speed=new_cmd._input)
				elif new_cmd._type == DIREX_CMD:
					if self.direx != 0 and new_cmd._input == 0:
						self.mc.changeDirex()
						self.direx = 0
					elif self.direx == 0 and new_cmd._input != 0:
						self.mc.changeDirex()
						self.direx = 1

			# off, so motor will enqueue commands until status-on command is received and then it
			# will resume operation and respond to all available commands in queue
			elif self.state == MCSTATE_MOTOROFF:
				new_cmd = self.cmd_list[0]
				if new_cmd._type == STATUS_CMD:
					if new_cmd._input:
						self.mc.toggle()
						self.state = self.last_state
					else:
						if WW_DEBUG: print('motor already off')
					del self.cmd_list[0]
				else:
					# if there is a command to turn it back on that is not in front, fast forward it to the front
					try:
						cmd_to_remove = next(a for a in self.cmd_list if a._type == STATUS_CMD and a._input > 0)
					except StopIteration:
						cmd_to_remove = None
					if cmd_to_remove is not None:
						self.cmd_list.remove(cmd_to_remove)
						self.mc.toggle()
						self.state = self.last_state

	# callback function for speed update flag that puts motor speed command in queue 
	def updateSpeed(self, desired_speed=0):
		if WW_DEBUG: print('updateSpeed being called. desired_speed = ', desired_speed)
		if desired_speed >= MC_Speed_Range[0] and desired_speed <= MC_Speed_Range[1]:
			new_spd_cmd = MCTask.cmd(SPEED_CMD, desired_speed)
			self.cmd_list.append(new_spd_cmd)
			if WW_DEBUG: print('cmd_list: ', self.cmd_list)
		else:
			if WW_DEBUG: print('desired speed not passed in, must be between 30 and 70');

	# callback function for status update flag that puts motor ON/OFF command in queue 
	def updateStatus(self, desired_status):
		if WW_DEBUG: print('calling updateStatus')
		new_status_cmd = MCTask.cmd(STATUS_CMD, desired_status)
		self.cmd_list.append(new_status_cmd)

	# callback function for direction update flag that puts motor direction command in queue
	def updateDirex(self, desired_direx):
		if WW_DEBUG: print('calling updateDirex')
		new_direx_cmd = MCTask.cmd(DIREX_CMD, desired_direx)
		self.cmd_list.append(new_direx_cmd)

	# callback function for connect flag that sets task active once BLE connection is made
	def setToRunning(self):
		self.state = MCSTATE_RUNNING

class BLETask:

	# initialize BLETask - attributes inlcude state, flags, mc_BLE from BLE_Class
	def __init__(self):
		self.state = BLESTATE_NOTCONNECTED
		self.task_id = TASKID_BLETASK
		Update_Desired_Speed_Flag = flag(fn=self.dummyMethod, ftype=FLAG_UPDATE_SPEED)
		Connection_Flag = flag(fn=None, ftype=FLAG_BLE_CONNECTED)
		Update_Status_Flag = flag(fn=None, ftype=FLAG_UPDATE_STATUS)
		Update_Direx_Flag = flag(fn=None, ftype=FLAG_UPDATE_DIREX)
		#order of flags in flag_list must follow order of flag enumeration, so that flags can be set using flag ID's
		self.flag_list = [Connection_Flag, Update_Status_Flag, Update_Desired_Speed_Flag, Update_Direx_Flag]
		self.ble = mc_BLE(server_role=True)

	# all tasks added must have a function called run
	def run(self):
		if WW_DEBUG: print('running BLETask');
		if self.state == BLESTATE_NOTCONNECTED:
			if self.ble.getConnectionStatus():
				self.state = BLESTATE_CONNECTED
				if WW_DEBUG: print('connection!!! in BLETask run');
				self.flag_list[BLE_ATTR_STATUS].setFlag()
		# check if an attribute has been written by client, then post command to MC_Task
		if (self.state == BLESTATE_CONNECTED):
			if self.ble.update_ready:
				# status (ON/OFF)
				if self.ble.attr_update_dict[BLE_ATTR_STATUS]:
					des_status = self.ble.server_readMotorCharacteristic(BLE_ATTR_STATUS)
					self.flag_list[FLAG_UPDATE_STATUS].setFlag(inp_param=des_status)
					self.ble.attr_update_dict[BLE_ATTR_STATUS] = 0 # unset update indicator
				#speed
				if self.ble.attr_update_dict[BLE_ATTR_SPEED]:
					des_speed = self.ble.server_readMotorCharacteristic(BLE_ATTR_SPEED)
					self.flag_list[FLAG_UPDATE_SPEED].setFlag(inp_param=des_speed)
					self.ble.attr_update_dict[BLE_ATTR_SPEED] = 0
				#direx
				if self.ble.attr_update_dict[BLE_ATTR_DIREX]:
					des_direx = self.ble.server_readMotorCharacteristic(BLE_ATTR_DIREX)
					self.flag_list[FLAG_UPDATE_DIREX].setFlag(inp_param=des_direx)
					self.ble.attr_update_dict[BLE_ATTR_DIREX] = 0
				self.ble.update_ready = False
				#reset
				if self.ble.attr_update_dict[BLE_ATTR_RESET]:
					if WW_DEBUG: print('calling reset')
					machine.reset()

	def dummyMethod(self):
		pass

# function called in Server boot that initializes and sets off entire system
def coopSchedScript():
	mt = MCTask()
	bt = BLETask()
	# task intervals must be higher than sys tick interval
	scheduler.addTask(mt, 180) #30
	scheduler.addTask(bt, 60) #30
	scheduler.run()

















