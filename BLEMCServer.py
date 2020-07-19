#Server - BLE/Motor Control Proj

from machine import Pin
from machine import Timer

from WWsched import coopSched
from WWsched import flag

from MC_Class import MC
from BLE_Class import mc_BLE

from BLE_Class import BLE_ATTR_STATUS
from BLE_Class import BLE_ATTR_SPEED
from BLE_Class import BLE_ATTR_DIREX

from micropython import const

#Toggle debug print statements
WW_DEBUG = const(0)

#Motor Controller states
MCSTATE_IDLE = const(1)
MCSTATE_RUNNING = const(2)
MCSTATE_SPEEDINGUP = const(3)
MCSTATE_SLOWINGDOWN = const(4)

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

scheduler = coopSched(tick_per_ms=1000, use_esp32=True) #per = period, not /

class MCTask:

	#intialize MCTask - state, MC() obj from MC_Class.py, and flags
	def __init__(self):
		self.task_id = TASKID_MCTASK
		self.state = MCSTATE_IDLE
		self.mc = MC()
		BLE_Updated_Desired_Speed_Flag = flag(fn=self.updateSpeed, ftype=FLAG_UPDATE_SPEED, take_param=True)
		BLE_Connected_Flag = flag(fn=self.setToRunning, ftype=FLAG_BLE_CONNECTED)
		Update_Status_Flag = flag(fn=self.updateStatus, ftype=FLAG_UPDATE_STATUS)
		Update_Direx_Flag = flag(fn=self.updateDirex, ftype=FLAG_UPDATE_DIREX)
		#order of flags in flag_list should follow order of flag enumeration
		self.flag_list = [BLE_Connected_Flag, Update_Status_Flag, BLE_Updated_Desired_Speed_Flag, Update_Direx_Flag]

	#all tasks added must have a function called run
	#run for MCtask prevents user from entering new speed until motor has reached desired speed
	#BLEtask will only set update speed flags once connected
	def run(self):
##############################################################################################################################

		# TODO - implement real thesholding, find some use for these states

##############################################################################################################################
		if WW_DEBUG: print('running MCTask');
		#task initial state - wait to take action until connected
		if self.state == MCSTATE_IDLE: 
			pass
		if self.state == MCSTATE_RUNNING:
			pass
		if self.state == MCSTATE_SPEEDINGUP:
			if (self.mc.speed < self.mc.target_speed):
				if WW_DEBUG: print('speed still adjusting')
				pass
			else:
				self.state = MCSTATE_RUNNING
		elif self.state == MCSTATE_SLOWINGDOWN:
			if (self.mc.speed > self.mc.target_speed):
				if WW_DEBUG: print('speed still adjusting')
				pass
			else:
				self.state = MCSTATE_RUNNING


	#callback function that updates motor speed
	def updateSpeed(self, desired_speed=0):
		if WW_DEBUG: print('updateSpeed being called. desired_speed = ', desired_speed)
		if desired_speed > MC_Speed_Range[0] and desired_speed < MC_Speed_Range[1]:
			if (desired_speed > self.mc.speed):
				self.state = MCSTATE_SPEEDINGUP
			else:
				self.state = MCSTATE_SLOWINGDOWN
			self.mc.useControl(use=True, speed=desired_speed)
		else:
			if WW_DEBUG: print('desired speed not passed in');

	#callback function that turns motor ON/OFF
	def updateStatus(self):
		if WW_DEBUG: print('calling updateStatus')
		self.mc.toggle()

	#callback function that updates motor direction
	def updateDirex(self):
		if WW_DEBUG: print('calling updateDirex')
		self.mc.changeDirex()

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
		self.des_speed = self.ble.server_readDesiredSpeed()
		self.last_des_speed = self.des_speed
		self.direx = True

	#all tasks added must have a function called run
	def run(self):
		if WW_DEBUG: print('running BLETask');
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
					self.flag_list[FLAG_UPDATE_STATUS].setFlag()
					self.ble.attr_update_dict[BLE_ATTR_STATUS] = 0
				#speed
				if self.ble.attr_update_dict[BLE_ATTR_SPEED]:
					self.des_speed = self.ble.server_readMotorCharacteristic(BLE_ATTR_SPEED)
					self.flag_list[FLAG_UPDATE_SPEED].setFlag(inp_param=self.des_speed)
					self.ble.attr_update_dict[BLE_ATTR_SPEED] = 0
				#direx
				if self.ble.attr_update_dict[BLE_ATTR_DIREX]:
					self.direx = self.ble.server_readMotorCharacteristic(BLE_ATTR_DIREX)
					self.flag_list[FLAG_UPDATE_DIREX].setFlag()
					self.ble.attr_update_dict[BLE_ATTR_DIREX] = 0
				self.ble.update_ready = False
			else:
				pass

	def dummyMethod(self):
		pass

def coopSchedScript():
	mt = MCTask()
	bt = BLETask()
	#task intervals must be higher than sys tick interval
	scheduler.addTask(mt, 3000)
	scheduler.addTask(bt, 3000)
	scheduler.run()

















