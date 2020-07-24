# cooperative scheduler class

#import pyb
import utime
#import uarray
from machine import Timer
from machine import Pin
import micropython

from micropython import const

micropython.alloc_emergency_exception_buf(100)

#show debug messages if 1
_WW_DEBUG = const(0)

#use timing GPIO if 1
_WW_TIMING = const(1)

#timing task & callbacks
_TIMING_TASK = const(0)
_TIMING_CALLBACK = const(1)

# turns on and off GPIO used to time tasks and flag callbacks on scope (if specified above)
class _TIMING_CONTEXT():

	def __init__(self, pin):
		self._pin = pin 

	def __enter__(self):
		if _WW_TIMING: self._pin.on()

	def __exit__(self, exc_type, exc_value, traceback):
		if _WW_TIMING: self._pin.off()
		return all(map(lambda x: x is None, [exc_type, exc_value, traceback]))


####################################################################################################################

												#TASK HANDLER#

####################################################################################################################

class coopSched:
	
	# tasks are imported as objects so that they can be run at regular intervals
	# interval should be significantly longer than input tick_per_ms
	class task:
		def __init__(self, user_task, per_ms):
			self._taskobj = user_task
			self._interval = per_ms
			self._last_tick = 0

	# Timer defined here always goes off every 1 ms... if you only want sys to run (check all flags) 
	# at (for example) 50 ms intervals, change coopSched._sys_tick_interval to 50. see run() below
	def __init__(self, tick_per_ms=1, use_esp32=False):   #1 ms as default period
		self._sys_tick_interval=tick_per_ms
		self._task_dict = {}
		self._task_ID_list = []
		if _WW_DEBUG: print('sys tick interval set to ', self._sys_tick_interval)
		self._tick_count = 0
		self._timing_pin = Pin(23, Pin.OUT)
		if use_esp32:
			sys_tick_int_tim=Timer(-1)
			sys_tick_int_tim.init(mode=Timer.PERIODIC, period=1, callback=self._tick)
		else:
			sys_tick_int_tim = Timer(mode=Timer.PERIODIC, period=1, callback=self._tick) #change period back to one
		self.flag_master_callback_ID_dict = {}

	# increase clock count
	def _tick(self, tym):
		self._tick_count = self._tick_count+1

	# add task to scheduler
	def add_task(self, user_task, per_ms):
		if per_ms < self._sys_tick_interval:
			raise Exception("task will run AT MOST at the same frequency as the scheduler tick")
		newTask = coopSched.task(user_task, per_ms)
		self._task_dict[user_task._task_ID] = newTask
		self._task_ID_list.append(user_task._task_ID)

	# for each faalg type, makes list of task ID's of the tasks that post/listen for this flag - comments in code clarify how
	def _add_callbacks_to_master_dict(self):
		for a in range(len(self._task_ID_list)):
			for b in range(len(self._task_dict[self._task_ID_list[a]]._taskobj._flag_list)):
				if (self._task_dict[self._task_ID_list[a]]._taskobj._flag_list[b].get_flag_type() not in self.flag_master_callback_ID_dict):
					# if you find a new type of flag, initialize a callback list for it in the master flag callback dict
					new_flag_added_ID = self._task_dict[self._task_ID_list[a]]._taskobj._flag_list[b].get_flag_type()
					self.flag_master_callback_ID_dict[new_flag_added_ID] = []
					#if you find a new key (flag), go through every task and check if it shares a flag... if so, add task's taskID to list
					for c in range(len(self._task_ID_list)):
						for d in range(len(self._task_dict[self._task_ID_list[c]]._taskobj._flag_list)):
							if self._task_dict[self._task_ID_list[c]]._taskobj._flag_list[d].get_flag_type() == new_flag_added_ID and self._task_dict[self._task_ID_list[c]]._taskobj._flag_list[d].flag_callback is not None:
								self.flag_master_callback_ID_dict[new_flag_added_ID].append(self._task_dict[self._task_ID_list[c]]._taskobj._task_ID)
		if _WW_DEBUG: print("callback dict:", self.flag_master_callback_ID_dict)

	# checks flags every time sys clock reaches number of ms defined by sys_tick_interval
	def run(self):

		if _WW_DEBUG: print('task dict: ', self._task_dict)
		if _WW_DEBUG: print('task id list: ', self._task_ID_list)
		self._add_callbacks_to_master_dict()

		while(True):
			if (self._tick_count % self._sys_tick_interval == 0):
				#check if flags are set then every sys_tick
				#rather than run through each task's flag list and run callbacks in order of task...
				#see a flag is set, run all callbacks associated with that flag
				if _WW_DEBUG: print('checking flags')
				serviced_flag_list = []
				#check though all flags in each task's flag list to see if they are set
				for a in range(len(self._task_ID_list)):
					for b in range(len(self._task_dict[self._task_ID_list[a]]._taskobj._flag_list)):
						curr_flag = self._task_dict[self._task_ID_list[a]]._taskobj._flag_list[b]
						#curr_flag = the actual flag in the task being checked
						if curr_flag.flag_set:
							# if flag is set and hasn't already been called from master callback dict
							if curr_flag.flag_type not in serviced_flag_list:
								set_flag_ID = curr_flag.flag_type
								#mark flag so it is ignored if set in other tasks
								serviced_flag_list.append(set_flag_ID)
								# if a flag is set, run its callbacks (from each task)
								if curr_flag.param is not None:
									param_to_use = curr_flag.param
									if _WW_DEBUG: print('this is param to use: ', param_to_use)

								#c = task ID of each task associated with a flag
								for c in self.flag_master_callback_ID_dict[set_flag_ID]:
									flag_to_service = self._task_dict[c]._taskobj._flag_list[set_flag_ID]
									# if flag has callback

									if flag_to_service.flag_callback is not None: #this line is unnecessary now - only callbacks are added
										#run flag callback with param if it has one
										if _TIMING_CALLBACK:
											with _TIMING_CONTEXT(self._timing_pin):
												if flag_to_service.takes_param:
													if _WW_DEBUG: print('running flag ', set_flag_ID, " from task ", c, " with param ", param_to_use)
													flag_to_service.flag_callback(param_to_use)
												else:
													if _WW_DEBUG: print('running flag ', set_flag_ID, " from task ", c)
													flag_to_service.flag_callback()
										else:
											if flag_to_service.takes_param:
												flag_to_service.flag_callback(param_to_use)
											else:
												flag_to_service.flag_callback()
						# unset flag - above structure (esp. serviced flag list) makes sure no flag callback gets run twice
						curr_flag.unset_flag()

				#run ongoing tasks at their specific intervals
				if _WW_DEBUG: print('running tasks')
				for a in range(len(self._task_ID_list)):
					if ((self._tick_count - self._task_dict[self._task_ID_list[a]]._last_tick) >= self._task_dict[self._task_ID_list[a]]._interval):
						if _TIMING_TASK:
							with _TIMING_CONTEXT(self._timing_pin):
								self._task_dict[self._task_ID_list[a]]._taskobj._run()
						else:
							self._task_dict[self._task_ID_list[a]]._taskobj._run()
						self._task_dict[self._task_ID_list[a]]._last_tick = self._tick_count
		self._tick_count = 0

####################################################################################################################

												#FLAG#

####################################################################################################################

# flag class contains callback assigned by task, flag type (identifier), flag status (set/unset), 
# indicator of whether or not caallback takes param, and flag param
class flag:
	def __init__(self,fn,ftype,take_param=False):
		self.flag_type = ftype
		self.flag_set = False
		self.flag_callback = fn
		self.param = None
		self.takes_param = take_param

	def set_flag(self, inp_param=None):
		self.flag_set = True
		if (inp_param is not None):
			self.param = inp_param

	def unset_flag(self):
		self.flag_set = False 

	def get_flag_type(self):
		return self.flag_type




















