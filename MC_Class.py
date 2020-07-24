#esp32 pwm test

from machine import Pin, PWM, Timer
from micropython import const 

# toggle debug print statements
_WW_DEBUG = const(0)

#Motor Constants
_FULL_DC = 1023
_FULL_ROTATION_TICKS = 368

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
		self._duty_cycle = 0
		self._pwm = PWM(Pin(21), freq=self.frequency, duty=self._duty_cycle)
		self._direx = Pin(22, Pin.OUT)
		self._direx.off()
		self._encoder_ticks_atm = 0 #atm = at the moment (since last check)
		self._encoder = Pin(19, Pin.IN)
		self._encoder.irq(trigger=Pin.IRQ_RISING, handler=self._add_encoder_tick)

		#controller timeout
		self._tim = Timer(2)
		self._tim.init(period=50, mode=Timer.PERIODIC, callback=self._calc_speed)
		self.speed = 0

		#controller target
		self._control_active = False
		self._target_speed = 0 #rpm
		self._sum_error = 0

	# set duty cycle to control output to motor
	def set_DC(self, DC):
		if self._direx.value() == 0: 
			self._duty_cycle = DC
			self._pwm.duty(self._duty_cycle)
		else:
			self._duty_cycle = _FULL_DC - DC
			self._pwm.duty(self._duty_cycle)

	# change direction of motor (CW/CCW). Also change duty cycle to fit
	# direction/direx pin
	def change_direx(self): 
		if self._direx.value() == 0: 
			self._direx.on()
			self.set_DC(DC=self._duty_cycle)
		else:
			self._direx.off()
			self.set_DC(DC=(_FULL_DC-self._duty_cycle))

	# turn motor on/off
	def toggle(self):
		self.use_control(use=False)
		if self._duty_cycle != 0:
			self._duty_cycle = 0
			if (self._direx.value() == 0):
				self._pwm.duty(0)
			else:
				self._pwm.duty(_FULL_DC)
		else:
			self.use_control(use=True, speed=self._target_speed)

	# toggle use of motor speed control. if control in use, also set desired speed
	def use_control(self, use=False, speed=0): #rpm
		self._control_active = use
		if use:
			self._target_speed = speed

	#callback that occurs when motor encoder registers a tick
	def _add_encoder_tick(self, pin):
		self._encoder_ticks_atm += 1

	#callback that calculates speed and implements controller when periodic control timer expires
	#speed: rpm = (ticks / 200 ms) (1 rev/ 368 ticks) (10*100 ms / 1 s) (60s / min)
	def _calc_speed(self, pin):
		self.last_speed = self.speed
		self.speed = 60*(self._encoder_ticks_atm*20)/_FULL_ROTATION_TICKS #should be rpm
		if _WW_DEBUG: print(self.speed)
		self._encoder_ticks_atm=0
		if (self._control_active):
			rpm_error = (self._target_speed - self.speed)
			self._sum_error += rpm_error	
			newDC = K_p * (rpm_error + (K_i * self._sum_error))
			if (newDC > 1023):
				newDC = 1023
				self._sum_error -= rpm_error
			elif (newDC < 0):
				newDC = 0
				self._sum_error -= rpm_error
			newDCint = int(newDC)
			self._duty_cycle=newDCint
			self.set_DC(DC=newDCint)

