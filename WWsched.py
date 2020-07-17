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
WW_DEBUG = const(0)

#use timing GPIO's
WW_TIMING = const(1)


#incorporate button state somehpw! - in WWschedtest.py

#aadd event checkers and continuous tasks

#create modules for SM and event checker - moved to WWES.py

#tick_count = 0

# def tick(tym):
# 	global tick_count
# 	tick_count = tick_count+1
	#toggleLEDPin()

#this timer always goes off every 1 ms... if you only want sys to run at 50 ms intervals, change coopSched.sys_tick_interval to 50
#timer can't go any faster

def calcTicksForTaskFreq(task_per, sys_per):
	return task_per/sys_per

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
		self.task_list = []
		if WW_DEBUG: print('sys tick interval set to ', self.sys_tick_interval);
		self.tick_count = 0
		if use_esp32:
			sys_tick_int_tim=Timer(-1)
			sys_tick_int_tim.init(mode=Timer.PERIODIC, period=1, callback=self.tick)
		else:
			sys_tick_int_tim = Timer(mode=Timer.PERIODIC, period=1, callback=self.tick) #change period back to one
		self.flag_master_callback_dict = {}
		if WW_TIMING:
			self.timing_pin = Pin(23, Pin.OUT)

	def toggleTimingPin(self):
		if self.timing_pin.value():
			self.timing_pin.off()
		else:
			self.timing_pin.on()

	def tick(self, tym):
		self.tick_count = self.tick_count+1

	def addTask(self, user_task, per_ms):
		if per_ms < self.sys_tick_interval:
			raise Exception("task will run AT MOST at the same frequency as the scheduler tick")
		newTask = coopSched.task(user_task, per_ms)
		self.task_list.append(newTask)

	def run(self):
		#add all flags to master list
		for a in range(len(self.task_list)):
			for b in range(len(self.task_list[a].taskobj.flag_list)):
				# if (self.task_list[a].taskobj.flag_list[b].getFlagname() not in self.flag_master_callback_dict):
				if (self.task_list[a].taskobj.flag_list[b].getFlagType() not in self.flag_master_callback_dict):
					# self.flag_master_callback_dict[self.task_list[a].taskobj.flag_list[b].getFlagname()] = []
					# if you find a new type of flag, initialize a callback list for it in the master flag callback dict
					self.flag_master_callback_dict[self.task_list[a].taskobj.flag_list[b].getFlagType()] = []
					#if you find a new key (flag), go through every task and check if it shares a flag... if so, add new callback to list
					# new_flag_added_name = self.task_list[a].taskobj.flag_list[b].getFlagname()
					new_flag_added_name = self.task_list[a].taskobj.flag_list[b].getFlagType()
					for c in range(len(self.task_list)):
						for d in range(len(self.task_list[c].taskobj.flag_list)):
							# if (self.task_list[c].taskobj.flag_list[d].getFlagname() == new_flag_added_name):
							if (self.task_list[c].taskobj.flag_list[d].getFlagType() == new_flag_added_name):
								self.flag_master_callback_dict[new_flag_added_name].append(self.task_list[c].taskobj.flag_list[d].flag_callback)
		print(self.flag_master_callback_dict)

		#create list of callbacks for each flag

		while(True):
			if (self.tick_count % self.sys_tick_interval == 0):
				#check flags and respond at sys tick interval rate
				# for a in range(len(self.task_list)):
				# 	for b in range(len(self.task_list[a].taskobj.flag_list)):
				# 		if self.task_list[a].taskobj.flag_list[b].flag_set:
				# 			print('set flag being checked')
				# 			self.task_list[a].taskobj.flag_list[b].flag_callback()
				# 			self.task_list[a].taskobj.flag_list[b].unsetFlag()

				#check if flags are set then every sys_tick
				#rather than run through each task's flag list and run callbacks in order of task...
				#see a flag is set, run all callbacks associated with that flag
				if WW_DEBUG: print('checking flags');
				serviced_flag_list = []
				#check though all flags in each task's flag list to see if they are set
				for a in range(len(self.task_list)):
					for b in range(len(self.task_list[a].taskobj.flag_list)):
						curr_flag = self.task_list[a].taskobj.flag_list[b]
						if curr_flag.flag_set 
							if curr_flag.flag_type not in serviced_flag_list:
								set_flag_ID = curr_flag.flag_type
								#mark flag so it is ignored if set in other tasks
								serviced_flags.append(set_flag_ID)
								# if a flag is set, run its callbacks (from each task)
								for c in range(len(self.flag_master_callback_dict[set_flag_ID])):
									# if there is a function
									if self.flag_master_callback_dict[set_flag_ID][c] is not None:
										#if the flag has a paaram

										#will this try to run all callbacks with curr_flag's param? :/

										if curr_flag.param is not None:
											#need a way to retrieve the flag FROM THE TASK corresponding to the callback so that we can get its param
											self.flag_master_callback_dict[set_flag_ID][c](self.task_list[a].taskobj.flag_list[b].param)
										else:
											self.flag_master_callback_dict[set_flag_ID][c]()
										#unset flag
										self.task_list[a].taskobj.flag_list[b].unsetFlag()
							else:
								curr_flag.unsetFlag()


					

					#add protection so that if multiple tasks set flag at same time, whole array won't get called twice


				#run ongoing tasks
				if WW_DEBUG: print('running tasks');
				for a in range(len(self.task_list)):
					if ((self.tick_count - self.task_list[a].last_tick) >= self.task_list[a].interval):
						#could use WITH here, like dmzella
						if WW_TIMING:
							self.timing_pin.on()
						self.task_list[a].taskobj.run()
						if WW_TIMING:
							self.timing_pin.off()
						self.task_list[a].last_tick = self.tick_count
		self.tick_count = 0

#WWsched: get rid of legacy code, add error checking for task frequency, fix flag callback bug'

####################################################################################################################

												#FLAG#

####################################################################################################################


class flag:
	def __init__(self,fn,ftype):
		# self.flag_name = name
		self.flag_type = ftype
		self.flag_set = False
		self.flag_callback = fn
		self.param = None
		# self.hasParam = False

	def setFlag(self, inp_param=None):
		self.flag_set = True
		if (inp_param is not None):
			self.param = inp_param

	def unsetFlag(self):
		self.flag_set = False 

	# def getFlagname(self):
	# 	return self.flag_type

	def getFlagType(self):
		return self.flag_type

#must find a way to add timeout stuff in here - debounce timer must change actual object in list




















