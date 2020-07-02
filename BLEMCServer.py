#Server - BLE/Motor Control Proj

# PSEUDO CODE

# initialize server

#template of task you can add to wwsched

from machine import Pin
from machine import Timer

from WWsched import coopSched
from WWsched import flag

from MC_Class import MC
from BLE_class import mc_BLE

from micropython import const

WW_DEBUG = const(1)

#need to edit coopSched to take classes instead of functions for tasks

# testLED=Pin('C9',Pin.OUT)
# button=Pin('C13', Pin.IN, pull=Pin.PULL_NONE)

MC_Speed_Range = [30, 70]
motor_attributes = ['sta', 'spd', 'drx']

# def YYY_flag_callback():
# 	if (testLED.value() == 0):
# 		testLED.on()
# 	else:
# 		testLED.off()

class MCTask:

	def __init__(self):
		# sensor sates
		# self.XXX_state = 
		# self.last_XXX_state = 
		self.state = 'idle'
		self.mc = MC()
		BLE_Updated_Desired_Speed_Flag = flag(fn=self.updateSpeed, name='ble_spd')
		BLE_Connected_Flag = flag(fn=self.setToRunning, name='ble_connected')
		Update_Status_Flag = flag(fn=self.updateStatus, name='ble_sta')
		Update_Direx_Flag = flag(fn=self.updateDirex, name='ble_drx')
		self.flag_list = [BLE_Connected_Flag, Update_Status_Flag, BLE_Updated_Desired_Speed_Flag, Update_Direx_Flag]

	#all tasks added must have a function called run
	def run(self):
		# TL;DR - if you're still getting up (or down) to speed, pass
		# TODO - implement real thesholding, find some use for these states
		if WW_DEBUG: print('running MCTask');
		if (self.state == 'running'):
			pass
		if (self.state == 'changing_speed_up'):
			if (self.mc.speed < self.mc.target_speed):
				pass
			else:
				self.state = 'running'
		elif (self.state == 'changing_speed_down'):
			if (self.mc.speed > self.mc.target_speed):
				pass
			else:
				self.state = 'running'

	
	def updateSpeed(self, desired_speed=0):
		if WW_DEBUG: print('updateSpeed being called. desired_speed = ', desired_speed)
		if desired_speed > MC_Speed_Range[0] and desired_speed < MC_Speed_Range[1]:
			#self.mc.target_speed = desired_speed
			if (desired_speed > self.mc.speed):
				self.state = 'changing_speed_up'
			else:
				self.state = 'changing_speed_down'
			self.mc.useControl(use=True, speed=desired_speed)
		else:
			if WW_DEBUG: print('desired speed not passed in');

	def updateStatus(self):
		if WW_DEBUG: print('calling updateStatus')
		self.mc.toggle()

	def updateDirex(self):
		if WW_DEBUG: print('calling updateDirex')
		self.mc.changeDirex()

	def setToRunning(self):
		self.state = 'running'

#WHEN EDITING SPEED IN BLUETILITY, MUST BE JUST DIGITS (NO 0x)
class BLETask:

	def __init__(self):
		self.state = 'not_connected'
		Update_Desired_Speed = flag(fn=self.dummyMethod, name='ble_spd')
		Connection_Flag = flag(fn=None, name='ble_connected')
		Update_Status_Flag = flag(fn=None, name='ble_sta')
		Update_Direx_Flag = flag(fn=None, name='ble_drx')
		self.flag_list = [Connection_Flag, Update_Status_Flag, Update_Desired_Speed, Update_Direx_Flag]
		self.ble = mc_BLE(server_role=True)
		self.status = True
		self.des_speed = self.ble.server_readDesiredSpeed()
		self.last_des_speed = self.des_speed
		self.direx = True

	#all tasks added must have a function called run
	def run(self):
		if WW_DEBUG: print('running BLETask');
		if self.state == 'not_connected':
			if self.ble.getConnectionStatus():
				self.state='connected'
				if WW_DEBUG: print('connection!!! in BLETask run');
				self.flag_list[1].setFlag()
		# event checker
		if (self.state == 'connected'):

			if self.ble.update_ready:
				#status
				if self.ble.attr_update_dict[motor_attributes[0]]:
					self.flag_list[1].setFlag()
					self.ble.attr_update_dict[motor_attributes[0]] = 0
				#speed
				if self.ble.attr_update_dict[motor_attributes[1]]:
					self.des_speed = self.ble.server_readMotorCharacteristic(motor_attributes[1])
					self.flag_list[2].setFlag(inp_param=self.des_speed)
					self.ble.attr_update_dict[motor_attributes[1]] = 0
				#direx
				if self.ble.attr_update_dict[motor_attributes[2]]:
					self.direx = self.ble.server_readMotorCharacteristic(motor_attributes[2])
					self.flag_list[3].setFlag()
					self.ble.attr_update_dict[motor_attributes[2]] = 0
			else:
				pass

			#(new_status, new_speed, new_direx) = self.ble.server_readMotorCharacteristics()

			# self.des_speed = self.ble.server_readDesiredSpeed() #do conversion in module
			# if WW_DEBUG: print('des_speed:', self.des_speed);
			# if (self.des_speed != self.last_des_speed):
			# 	if WW_DEBUG: print('new desired_speed: ', self.des_speed);
			# 	self.flag_list[0].setFlag(inp_param=self.des_speed)
			# self.last_des_speed = self.des_speed






	# SET UP A GATTS NOTIFY FOR WHEN MOTOR HAS REACHED ITS TARGET SPEED

	def dummyMethod(self, speed_nm):
		pass

def coopSchedScript():
	mt = MCTask()
	bt = BLETask()
	scheduler = coopSched(tick_per_ms=1000, use_esp32=True) #per = period, not /
	scheduler.addTask(mt, 3000)
	scheduler.addTask(bt, 3000)
	scheduler.run()






















