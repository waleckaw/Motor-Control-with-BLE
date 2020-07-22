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
WW_DEBUG = const(1)

#Motor Controller states
MCSTATE_IDLE = const(1)
MCSTATE_RUNNING = const(2)
MCSTATE_SPEEDINGUP = const(3)
MCSTATE_SLOWINGDOWN = const(4)
MCSTATE_MOTOROFF = const(5)

#esp32 BLE states
BLESTATE_NOTCONNECTED = const(1)
BLESTATE_CONNECTED = const(2)

#esp32 flags
FLAG_BLE_CONNECTED = const(0)
FLAG_UPDATE_STATUS = const(1)
FLAG_UPDATE_SPEED = const(2)
FLAG_UPDATE_DIREX = const(3)

TASKID_MCTASK =const(0)
TASKID_BLETASK =const(1)

MC_Speed_Range = [30, 70]

scheduler = coopSched(tick_per_ms=30, use_esp32=True) #per = period, not /

class MCTask:

	STATUS_CMD = const(0)
	SPEED_CMD = const(1)
	DIREX_CMD = const(2)

	SPEED_THRESHOLD_BUF = 3

	#intialize MCTask - state, MC() obj from MC_Class.py, and flags
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

	class cmd:

		def __init__(self, type, input=0):
			self._type = type
			self._input = input

	#all tasks added must have a function called run
	#run for MCtask prevents user from entering new speed until motor has reached desired speed
	#BLEtask will only set update speed flags once connected
	def run(self):
		if WW_DEBUG: print('running MCTask, state = ', self.state);
		#if WW_DEBUG: print('cmd_queue =', self.cmd_list)
		#task initial state - wait to take action until connected
		if self.state == MCSTATE_IDLE: 
			return
		#check if motor has reached target speed
		if self.state == MCSTATE_SPEEDINGUP and self.mc.speed > (self.mc.target_speed - self.SPEED_THRESHOLD_BUF):
			self.state = MCSTATE_RUNNING
		elif self.state == MCSTATE_SLOWINGDOWN and self.mc.speed < (self.mc.target_speed + self.SPEED_THRESHOLD_BUF):
			self.state = MCSTATE_RUNNING
		if not self.cmd_list:
			return
		else:
			# need to make sure if it stops, it restarts with desired speed
			if self.state == MCSTATE_SPEEDINGUP:
				#must create mc_class command that accepts on/off input (not just toggle)
				#maybe one for direx that aaccepts input as well
				new_cmd = self.cmd_list.pop(0)
				if new_cmd._type == SPEED_CMD:
					#put cmd at index 1 so run takes next cmd next time but then tries speed cmd again 
					#if more than one speed cmd in the queue, they will flip-flop until current cmd is achieved
					self.cmd_list.append(new_cmd)
					if WW_DEBUG: print('cmd_list: ', self.cmd_list)
				if new_cmd._type == STATUS_CMD:
					self.mc.toggle()
					self.last_state = self.state
					self.state = MCSTATE_MOTOROFF
				elif new_cmd._type == DIREX_CMD:
					#change direx but still speeding up
					#if using Bluetility, can't assume user will input 1
					if self.direx != 0 and new_cmd._input == 0:
						self.mc.changeDirex()
						self.direx = 0
					elif self.direx == 0 and new_cmd._input != 0:
						self.mc.changeDirex()
						self.direx = 1

			elif self.state == MCSTATE_SLOWINGDOWN:
				#must create mc_class command that accepts on/off input (not just toggle)
				#maybe one for direx that aaccepts input as well
				new_cmd = self.cmd_list.pop(0)
				if new_cmd._type == SPEED_CMD:
					#put cmd at index 1 so run takes next cmd next time but then tries speed cmd again 
					self.cmd_list.append(new_cmd)
					if WW_DEBUG: print('cmd_list: ', self.cmd_list)
				if new_cmd._type == STATUS_CMD:
					self.mc.toggle()
					self.last_state = self.state
					self.state = MCSTATE_MOTOROFF
				elif new_cmd._type == DIREX_CMD:
					#change direx but still speeding up
					if self.direx != 0 and new_cmd._input == 0:
						self.mc.changeDirex()
						self.direx = 0
					elif self.direx == 0 and new_cmd._input != 0:
						self.mc.changeDirex()
						self.direx = 1

			#running, so you can now take speed cmds
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

			#off, so you only change if cmd is for status
			elif self.state == MCSTATE_MOTOROFF:
				new_cmd = self.cmd_list.pop(0)
				if new_cmd._type == STATUS_CMD:
					#must add input here	
					if new_cmd._input:
						self.mc.toggle()
						self.state = self.last_state
					else:
						if WW_DEBUG: print('motor already off')
				else:
					# this will screw up order of commands as defined by user. what you should 
					# really do is find first instance of turn on cmd and move it to the front
					self.cmd_list.append(new_cmd)
				

	#callback function that updates motor speed
	# def updateSpeed(self, desired_speed=0):
	# 	if WW_DEBUG: print('updateSpeed being called. desired_speed = ', desired_speed)
	# 	if desired_speed >= MC_Speed_Range[0] and desired_speed <= MC_Speed_Range[1]:
	# 		if (desired_speed > self.mc.speed):
	# 			self.state = MCSTATE_SPEEDINGUP
	# 		else:
	# 			self.state = MCSTATE_SLOWINGDOWN
	# 		self.mc.useControl(use=True, speed=desired_speed)
	# 	else:
	# 		if WW_DEBUG: print('desired speed not passed in');

	def updateSpeed(self, desired_speed=0):
		#could make this aa lambda function to post to the list
		if WW_DEBUG: print('updateSpeed being called. desired_speed = ', desired_speed)
		if desired_speed >= MC_Speed_Range[0] and desired_speed <= MC_Speed_Range[1]:
			new_spd_cmd = MCTask.cmd(SPEED_CMD, desired_speed)
			self.cmd_list.append(new_spd_cmd)
		else:
			if WW_DEBUG: print('desired speed not passed in, must be between 30 and 70');

	#callback function that turns motor ON/OFF
	def updateStatus(self, desired_status):
		if WW_DEBUG: print('calling updateStatus')
		#self.mc.toggle()
		new_status_cmd = MCTask.cmd(STATUS_CMD, desired_status)
		self.cmd_list.append(new_status_cmd)

	#callback function that updates motor direction
	def updateDirex(self, desired_direx):
		if WW_DEBUG: print('calling updateDirex')
		# self.mc.changeDirex()
		new_direx_cmd = MCTask.cmd(DIREX_CMD, desired_direx)
		self.cmd_list.append(new_direx_cmd)

	#callback function that sets task active once BLE connection is made
	def setToRunning(self):
		self.state = MCSTATE_RUNNING

class BLETask:

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
		self.status = True
		#self.des_speed = self.ble.server_readDesiredSpeed()
		#self.last_des_speed = self.des_speed
		#self.direx = 1 #1=fwd, 0=rvrs

	#all tasks added must have a function called run
	def run(self):
		#if WW_DEBUG: print('running BLETask');
		if self.state == BLESTATE_NOTCONNECTED:
			if self.ble.getConnectionStatus():
				self.state = BLESTATE_CONNECTED
				if WW_DEBUG: print('connection!!! in BLETask run');
				self.flag_list[BLE_ATTR_STATUS].setFlag()
		# event checker
		if (self.state == BLESTATE_CONNECTED):
			if self.ble.update_ready:
				#status (ON/OFF)
				if self.ble.attr_update_dict[BLE_ATTR_STATUS]:
					des_status = self.ble.server_readMotorCharacteristic(BLE_ATTR_STATUS)
					self.flag_list[FLAG_UPDATE_STATUS].setFlag(inp_param=des_status)
					self.ble.attr_update_dict[BLE_ATTR_STATUS] = 0
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
			else:
				pass

	def dummyMethod(self):
		pass

def coopSchedScript():
	mt = MCTask()
	bt = BLETask()
	#task intervals must be higher than sys tick interval
	scheduler.addTask(mt, 180) #30
	scheduler.addTask(bt, 60) #30
	scheduler.run()

















