#esp32 pwm test

from machine import Pin, PWM, Timer
from micropython import const 

# toggle debug print statements
WW_DEBUG = const(0)

#Motor Constants
FULL_DC = 1023
FULL_ROTATION_TICKS = 368

# Motor Control Constants
K_p = 10 # Purposefully under-damped for slow response to validate state change behavior
K_i = 0.1
K_d = 0.2

# class used to operate motor
class MC:

	# initialize Motor Controller - attributes include PWM frequency, PWM and direction pins to motor driver,
	# interrupt pin to count encoder ticks, controller update interrupt timer, speed, target speed, and more
	def __init__(self, freq=1500, DC=512):
		self.frequency = freq
		self.duty_cycle = 0
		self.pwm = PWM(Pin(21), freq=self.frequency, duty=self.duty_cycle)
		self.direx = Pin(22, Pin.OUT)
		self.direx.off()
		self.encoder_ticks_atm = 0 #atm = at the moment (since last check)
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

	# allows user to adjust controller frequency from REPL
	def setFreq(self, freq):
		self.frequency=freq

	# set duty cycle to control output to motor
	def setDC(self, DC):
		if self.direx.value() == 0: 
			self.duty_cycle = DC
			self.pwm.duty(self.duty_cycle)
		else:
			self.duty_cycle = FULL_DC - DC
			self.pwm.duty(self.duty_cycle)

	# change direction of motor (CW/CCW). Also change duty cycle to fit
	# direction/direx pin
	def changeDirex(self): 
		if self.direx.value() == 0: 
			self.direx.on()
			self.setDC(DC=self.duty_cycle)
		else:
			self.direx.off()
			self.setDC(DC=(FULL_DC-self.duty_cycle))

	# turn motor on/off
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

	# toggle use of motor speed control. if control in use, also set desired speed
	def useControl(self, use=False, speed=0): #rpm
		self.use_control = use
		#self.sum_error = 0
		if use:
			self.target_speed = speed

	#callback that occurs when motor encoder registers a tick
	def addEncoderTick(self, pin):
		self.encoder_ticks_atm += 1

	#callback that calculates speed and implements controller when periodic control timer expires
	#speed: rpm = (ticks / 200 ms) (1 rev/ 368 ticks) (10*100 ms / 1 s) (60s / min)
	def calcSpeed(self, pin):
		self.last_speed = self.speed
		self.speed = 60*(self.encoder_ticks_atm*20)/FULL_ROTATION_TICKS #should be rpm
		if WW_DEBUG: print(self.speed);
		self.encoder_ticks_atm=0
		if (self.use_control):
			rpm_error = (self.target_speed - self.speed)
			self.sum_error += rpm_error	
			newDC = K_p * (rpm_error + (K_i * self.sum_error))
			if (newDC > 1023):
				newDC = 1023
				self.sum_error -= rpm_error
			elif (newDC < 0):
				newDC = 0
				self.sum_error -= rpm_error
			newDCint = int(newDC)
			self.duty_cycle=newDCint
			self.setDC(DC=newDCint)

