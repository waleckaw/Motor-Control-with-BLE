#esp32 pwm test

from machine import Pin, PWM, Timer
from micropython import const 

WW_DEBUG = const(0)

FULL_DC = 1023
FULL_ROTATION_TICKS = 368

K_p = 20
K_i = 0.1
K_d = 0.2

class MC:

	def __init__(self, freq=1500, DC=512):
		self.frequency = freq
		self.duty_cycle = 0
		self.pwm = PWM(Pin(21), freq=self.frequency, duty=self.duty_cycle)
		self.direx = Pin(22, Pin.OUT)
		self.direx.off()

		self.encoder_ticks_atm = 0

		self.encoder = Pin(19, Pin.IN)
		self.encoder.irq(trigger=Pin.IRQ_RISING, handler=self.addEncoderTick)

		#controller timeout
		self.tim = Timer(2)
		self.tim.init(period=50, mode=Timer.PERIODIC, callback=self.calcSpeed)
		self.speed = 0
		self.printct = 0

		#controller target
		self.use_control = False
		self.target_speed = 0 #rpm
		self.sum_error = 0

		#self.speedCalcTimer = 

	def setFreq(self, freq):
		self.frequency=freq
		# pwm.freq(self.frequency)

	def setDC(self, DC):
		if self.direx.value() == 0: #if direx is CCW IE direx pin is low
			self.duty_cycle = DC
			self.pwm.duty(self.duty_cycle)
		else:					#if direx is CW IE direx pin is High
			self.duty_cycle = FULL_DC - DC
			self.pwm.duty(self.duty_cycle)

	def changeDirex(self): #if direx is CCW IE direx pin is low
		if self.direx.value() == 0: 
			self.direx.on()
			self.setDC(DC=self.duty_cycle)
		else:
			self.direx.off()
			self.setDC(DC=(FULL_DC-self.duty_cycle))

	def toggle(self):
		self.useControl(use=False)
		if self.duty_cycle != 0:
			self.duty_cycle = 0
			if (self.direx.value() == 0):
				self.pwm.duty(0)
			else:
				self.pwm.duty(FULL_DC)
		else:
			self.useControl(use=True, speed=self.target_speed)

	def useControl(self, use=False, speed=0): #rpm
		self.use_control = use
		#self.sum_error = 0
		if (self.use_control):
			self.target_speed = speed

	def addEncoderTick(self, pin):
		self.encoder_ticks_atm += 1

	def calcSpeed(self, pin):
		#speed: rpm = (ticks / 200 ms) (1 rev/ 368 ticks) (10*100 ms / 1 s) (60s / min)
		self.last_speed = self.speed
		self.speed = 60*(self.encoder_ticks_atm*20)/FULL_ROTATION_TICKS #should be rpm
		if WW_DEBUG: print(self.speed);
		self.encoder_ticks_atm=0
		
		#printing stuff - will hurt controller, disable when u get close
		# self.printct += 1
		# if self.printct == 10:
		# 	self.printct = 0
		# 	print(self.speed)

		#control stuff
		if (self.use_control):
			#if (self.direx.value() == 0): #if direx is CCW IE direx pin is LOW
			#may only work going up
			# /time fro derivative constant included in K_d
			# if (self.target_speed > self.speed):
			rpm_error = (self.target_speed - self.speed)
			#damping
			self.sum_error += rpm_error	
			newDC = K_p * (rpm_error + (K_i * self.sum_error))
			if (newDC > 1023):
				newDC = 1023
				self.sum_error -= rpm_error
			elif (newDC < 0):
				newDC = 0
				self.sum_error -= rpm_error
			# else:
			# 	rpm_error = (self.speed - self.target_speed)
			# 	self.sum_error += rpm_error
			# 	newDC = K_p * (rpm_error + (K_i * sum_error))
			newDCint = int(newDC)
			# print(newDCint) 
			self.duty_cycle=newDCint
			self.setDC(DC=newDCint)

	def __del__(self):
		self.tim.deinit()

