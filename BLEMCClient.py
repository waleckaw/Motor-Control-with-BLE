#Server - BLE/Motor Control Proj

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

# def YYY_flag_callback():
# 	if (testLED.value() == 0):
# 		testLED.on()
# 	else:
# 		testLED.off()

#WHEN EDITING SPEED IN BLUETILITY, MUST BE JUST DIGITS (NO 0x)
class BLETask:

	def __init__(self):
		self.state = 'not_connected'
		# Update_Desired_Speed = flag(fn=self.dummyMethod, name='ble_update')
		# Connection_Flag = flag(fn=None, name='ble_connected')
		# self.flag_list = [Update_Desired_Speed, Connection_Flag]
		self.flag_list = []
		self.ble = mc_BLE()
		# self.des_speed = self.ble.readDesiredSpeed()
		# self.last_des_speed = self.des_speed

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
			self.des_speed = self.ble.readDesiredSpeed() #do conversion in module
			if WW_DEBUG: print('des_speed:', self.des_speed);
			if (self.des_speed != self.last_des_speed):
				if WW_DEBUG: print('new desired_speed: ', self.des_speed);
				self.flag_list[0].setFlag(inp_param=self.des_speed)
			self.last_des_speed = self.des_speed

	def dummyMethod(self, speed_nm):
		pass

def coopSchedScript():
	bt = BLETask()
	scheduler = coopSched(tick_per_ms=1000, use_esp32=True) #per = period, not /
	scheduler.addTask(bt, 3000)
	scheduler.run()






















