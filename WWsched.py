# cooperative scheduler class

#import pyb
import utime
#import uarray
from machine import Timer
from machine import Pin
import micropython

from micropython import const

micropython.alloc_emergency_exception_buf(100)

#show debug messages
WW_DEBUG = const(1)

#use timing GPIO
WW_TIMING = const(1)

#timing task & caallbacks
TIMING_TASK = const(0)
TIMING_CALLBACK = const(1)

class TIMING_CONTEXT(object):

	def __init__(self, pin):
		self._pin = pin 

	def __enter__(self):
		if WW_TIMING: self._pin.on()

	def __exit__(self, exc_type, exc_value, traceback):
		if WW_TIMING: self._pin.off()
		return all(map(lambda x: x is None, [exc_type, exc_value, traceback]))


####################################################################################################################

												#TASK HANDLER#

####################################################################################################################

class coopSched:
	#somehow adding one of these should be like adding something to es framework... run function etc
	class task:
		def __init__(self, user_task, per_ms):
			self.taskobj = user_task
			self.interval = per_ms #watch out to make sure this period is considerably longer than tick_interval
			self.last_tick = 0

	def __init__(self, tick_per_ms=1, use_esp32=False):   #1 ms as default period
		self.track_var = False
		self.sys_tick_interval=tick_per_ms
		# self.task_list = []
		self.task_dict = {}
		self.task_id_list = []
		if WW_DEBUG: print('sys tick interval set to ', self.sys_tick_interval);
		self.tick_count = 0
		self._timing_pin = Pin(23, Pin.OUT)
		#Timer defined here always goes off every 1 ms... if you only want sys to run at 50 ms intervals, change coopSched.sys_tick_interval to 50
		#timer can't go any faster
		if use_esp32:
			sys_tick_int_tim=Timer(-1)
			sys_tick_int_tim.init(mode=Timer.PERIODIC, period=1, callback=self.tick)
		else:
			sys_tick_int_tim = Timer(mode=Timer.PERIODIC, period=1, callback=self.tick) #change period back to one
		self.flag_master_callback_ID_dict = {}

	# def toggleTimingPin(self):
	# 	if self.timing_pin.value():
	# 		self.timing_pin.off()
	# 	else:
	# 		self.timing_pin.on()

	def tick(self, tym):
		self.tick_count = self.tick_count+1

	def addTask(self, user_task, per_ms):
		if per_ms < self.sys_tick_interval:
			raise Exception("task will run AT MOST at the same frequency as the scheduler tick")
		newTask = coopSched.task(user_task, per_ms)
		# self.task_list.append(newTask)
		self.task_dict[user_task.task_id] = newTask
		self.task_id_list.append(user_task.task_id)

	def __addCallbacksToMasterDict(self):
		#add all flag callback task ID's to master list
		for a in range(len(self.task_id_list)):
			for b in range(len(self.task_dict[self.task_id_list[a]].taskobj.flag_list)):
				if (self.task_dict[self.task_id_list[a]].taskobj.flag_list[b].getFlagType() not in self.flag_master_callback_ID_dict):
					# if you find a new type of flag, initialize a callback list for it in the master flag callback dict
					new_flag_added_ID = self.task_dict[self.task_id_list[a]].taskobj.flag_list[b].getFlagType()
					self.flag_master_callback_ID_dict[new_flag_added_ID] = []
					#if you find a new key (flag), go through every task and check if it shares a flag... if so, add new callback to list
					for c in range(len(self.task_id_list)):
						for d in range(len(self.task_dict[self.task_id_list[c]].taskobj.flag_list)):
							if self.task_dict[self.task_id_list[c]].taskobj.flag_list[d].getFlagType() == new_flag_added_ID and self.task_dict[self.task_id_list[c]].taskobj.flag_list[d].flag_callback is not None:
								self.flag_master_callback_ID_dict[new_flag_added_ID].append(self.task_dict[self.task_id_list[c]].taskobj.task_id)
		if WW_DEBUG: print("callback dict:", self.flag_master_callback_ID_dict)

	def run(self):

		#create list of callbacks for each flag

		if WW_DEBUG: print('task dict: ', self.task_dict)
		if WW_DEBUG: print('task id list: ', self.task_id_list)

		self.__addCallbacksToMasterDict()

		while(True):
			if (self.tick_count % self.sys_tick_interval == 0):
				#check if flags are set then every sys_tick
				#rather than run through each task's flag list and run callbacks in order of task...
				#see a flag is set, run all callbacks associated with that flag
				if WW_DEBUG: print('checking flags');
				serviced_flag_list = []
				#check though all flags in each task's flag list to see if they are set
				for a in range(len(self.task_id_list)):
					for b in range(len(self.task_dict[self.task_id_list[a]].taskobj.flag_list)):
						curr_flag = self.task_dict[self.task_id_list[a]].taskobj.flag_list[b]
						#curr_flag = the actual flag in the task that you are checking
						if curr_flag.flag_set:
							# if flag is set and hasn't already been called from master callback dict
							if curr_flag.flag_type not in serviced_flag_list:
								set_flag_ID = curr_flag.flag_type
								#mark flag so it is ignored if set in other tasks
								serviced_flag_list.append(set_flag_ID)
								# if a flag is set, run its callbacks (from each task)
								if curr_flag.param is not None:
									param_to_use = curr_flag.param
									if WW_DEBUG: print('this is param to use: ', param_to_use)

								#c = task ID of each task associated with a flag
								for c in self.flag_master_callback_ID_dict[set_flag_ID]:
									flag_to_service = self.task_dict[c].taskobj.flag_list[set_flag_ID]
									# if flag has callback

									if flag_to_service.flag_callback is not None: #this line is unnecessary now - only callbacks are added
										#run flag callback with param if it has one
										if TIMING_CALLBACK:
											with TIMING_CONTEXT(self._timing_pin):
												if flag_to_service._take_param:
													if WW_DEBUG: print('running flag ', set_flag_ID, " from task ", c, " with param ", param_to_use)
													flag_to_service.flag_callback(param_to_use)

												else:
													if WW_DEBUG: print('running flag ', set_flag_ID, " from task ", c)
													flag_to_service.flag_callback()
										else:
											if flag_to_service._take_param:
												flag_to_service.flag_callback(param_to_use)
											else:
												flag_to_service.flag_callback()
								#This should also ensure that if flag set in other task but already has been checked, unset and ignore
						curr_flag.unsetFlag()

				#run ongoing tasks
				if WW_DEBUG: print('running tasks');
				for a in range(len(self.task_id_list)):
					if ((self.tick_count - self.task_dict[self.task_id_list[a]].last_tick) >= self.task_dict[self.task_id_list[a]].interval):
						if TIMING_TASK:
							with TIMING_CONTEXT(self._timing_pin):
								self.task_dict[self.task_id_list[a]].taskobj.run()
						else:
							self.task_dict[self.task_id_list[a]].taskobj.run()
						self.task_dict[self.task_id_list[a]].last_tick = self.tick_count
		self.tick_count = 0

####################################################################################################################

												#FLAG#

####################################################################################################################

class flag:
	def __init__(self,fn,ftype,take_param=False):
		# self.flag_name = name
		self.flag_type = ftype
		self.flag_set = False
		self.flag_callback = fn
		self.param = None
		self._take_param = take_param
		# self.hasParam = False

	def setFlag(self, inp_param=None):
		self.flag_set = True
		if (inp_param is not None):
			self.param = inp_param

	def unsetFlag(self):
		self.flag_set = False 

	def getFlagType(self):
		return self.flag_type




















