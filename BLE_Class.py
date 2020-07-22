# only compatible with unstable builds for esp32

# https://www.oreilly.com/library/view/getting-started-with/9781491900550/ch04.html
# It is worth mentioning once more that GATT roles are both completely independent of GAP roles (see “Roles”) and also concurrently 
# compatible with each other. That means that both a GAP central and a GAP peripheral can act as a GATT client or server, 
# or even act as both at the same time.


import ubluetooth
import utime
import struct
import utime

from micropython import const
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)
_IRQ_PERIPHERAL_CONNECT = const(7)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTC_SERVICE_RESULT = const(9)
_IRQ_GATTC_CHARACTERISTIC_RESULT = const(11)
_IRQ_GATTC_CHARACTERISTIC_DONE = const(12)
_IRQ_GATTC_READ_RESULT = const(15)
_IRQ_GATTC_READ_DONE = const(16)
_IRQ_GATTC_WRITE_DONE = const(17)

WW_DEBUG = const(1)

adv_type_dict = {0x00: 'ADV_IND - connectable and scannable undirected advertising',
0x01: 'ADV_DIRECT_IND - connectable directed advertising',
0x02: 'ADV_SCAN_IND - scannable undirected advertising',
0x03: 'ADV_NONCONN_IND - non-connectable undirected advertising',
0x04: 'SCAN_RSP - scan response'}

_WW_MAC_ADDR = b'xOCT\xf5\x00'
_SERVER_ADDR = b'$b\xab\xf9\x0bR'
_CLIENT_ADDR = b'$b\xab\xf9\x17\xd6'
#_WW_MAC_ADDR = b'\x78\x4f\x43\x54\xf5\x00'

#attribute indicators
BLE_ATTR_STATUS = const(0)
BLE_ATTR_SPEED = const(1)
BLE_ATTR_DIREX = const(2)
BLE_ATTR_RESET = const(3)


CUSTOM_MOTOR_CONTROL_SERVICE_UUID = ubluetooth.UUID('1ab35ef6-b76b-11ea-b3de-0242ac130004')

STATUS_UUID = ubluetooth.UUID('dac11e24-ba93-11ea-b3de-0242ac130004')
CUSTOM_STATUS_CHAR = (STATUS_UUID, ubluetooth.FLAG_WRITE | ubluetooth.FLAG_READ,)
DESIRED_SPEED_UUID = ubluetooth.UUID('a0ad58b2-b76c-11ea-b3de-0242ac130004')
CUSTOM_DESIRED_SPEED_CHAR = (DESIRED_SPEED_UUID, ubluetooth.FLAG_WRITE | ubluetooth.FLAG_READ,)
DIREX_UUID = ubluetooth.UUID('c6f75c74-ba88-11ea-b3de-0242ac130004')
CUSTOM_DESIRED_DIREX_CHAR = (DIREX_UUID, ubluetooth.FLAG_WRITE | ubluetooth.FLAG_READ,)

RESET_UUID = ubluetooth.UUID('36ca78c0-ca32-11ea-87d0-0242ac130003')
CUSTOM_DESIRED_RESET_CHAR = (RESET_UUID, ubluetooth.FLAG_WRITE)

CUSTOM_MOTOR_CONTROL_SERVICE = (CUSTOM_MOTOR_CONTROL_SERVICE_UUID, (CUSTOM_STATUS_CHAR, CUSTOM_DESIRED_SPEED_CHAR, CUSTOM_DESIRED_DIREX_CHAR, CUSTOM_DESIRED_RESET_CHAR,),)
SERVICE_LIST = (CUSTOM_MOTOR_CONTROL_SERVICE,)

class mc_BLE:

	def __init__(self, pier_addr=_SERVER_ADDR, server_role=False):
		self.addr_list = []
		self.pier=pier_addr
		self.bl = ubluetooth.BLE()
		self.bl.active(True)
		self.connected = False
		self.bl.irq(handler=self.bt_irq)
		self.is_server=server_role
		#next 3 maay be for server only - - - need to check
		self.update_ready=False
		self.attr_update_dict = {BLE_ATTR_STATUS: 0, BLE_ATTR_SPEED: 0, BLE_ATTR_DIREX: 0, BLE_ATTR_RESET: 0}

		self.__get_info()
		if server_role:
			#serv_ refers to server, not service
			((self.serv_status_value_handle, self.serv_speed_value_handle, self.serv_direx_value_handle, self.serv_reset_value_handle),) = self.bl.gatts_register_services(SERVICE_LIST)
			# self.attr_handle_dict = {'sta': self.serv_status_value_handle, 'spd': self.serv_speed_value_handle, 'drx': self.serv_direx_value_handle}
			self.attr_handle_dict = {BLE_ATTR_STATUS: self.serv_status_value_handle, BLE_ATTR_SPEED: self.serv_speed_value_handle, BLE_ATTR_DIREX: self.serv_direx_value_handle, BLE_ATTR_RESET: self.serv_reset_value_handle}
			self.advertise()
		else:
			self.scan()
	# BLE.irq calls bt_irq with specific event input and data input
	# bt_irq just assigns the data from ble.irq to variables (ie: conn_handle, addr_type, addr)
	def bt_irq(self, event, data):
		if event == _IRQ_CENTRAL_CONNECT:
			# A central has connected to this peripheral.

			conn_handle, addr_type, addr = data
			if WW_DEBUG: print('connection from central');
			self.connected = True

		elif event == _IRQ_GATTS_WRITE:
			# A central has written to this characteristic or descriptor.
			if WW_DEBUG: print('central has written')
			self.update_ready = True
			conn_handle, attr_handle = data
			if attr_handle == self.serv_status_value_handle:
				self.attr_update_dict[BLE_ATTR_STATUS] = 1
			elif attr_handle == self.serv_speed_value_handle:
				self.attr_update_dict[BLE_ATTR_SPEED] = 1
			elif attr_handle == self.serv_direx_value_handle:
				self.attr_update_dict[BLE_ATTR_DIREX] = 1
			elif attr_handle == self.serv_reset_value_handle:
				self.attr_update_dict[BLE_ATTR_RESET] = 1

		elif event == _IRQ_CENTRAL_DISCONNECT:
			# A central has disconnected from this peripheral.
			conn_handle, addr_type, addr = data
			#must be a server for this to happen
			self.advertise()

		elif event == _IRQ_SCAN_RESULT:
			addr_type, addr, adv_type, rssi, adv_data = data
			new_addr = bytes(addr)
			# A single scan result.
			if addr == self.pier:
				self.__cnxToMyPC()
				self.__stopScan()
			elif new_addr not in self.addr_list:
					self.addr_list.append(new_addr)
					print('suxes. addr_type = ', addr_type, 'addr = ', addr, 'adv_type = ', adv_type, ': ', adv_type_dict[adv_type], 'adv_data = ', adv_data)
					self.__decodeAddress(addr)
					decodeAdvData(adv_data)
		elif event == _IRQ_SCAN_DONE:
			# Scan duration finished or manually stopped.
			pass

		elif event == _IRQ_PERIPHERAL_CONNECT:
			# A successful gap_connect().
			self.server_conn_handle, addr_type, addr = data
			print('peripheral connect')
			self.bl.gattc_discover_services(self.server_conn_handle)

		elif event == _IRQ_GATTC_SERVICE_RESULT:
			# Called for each service found by gattc_discover_services().
			conn_handle, start_handle, end_handle, uuid = data
			if conn_handle == self.server_conn_handle:
				if uuid == CUSTOM_MOTOR_CONTROL_SERVICE_UUID:
					self.bl.gattc_discover_characteristics(self.server_conn_handle, start_handle, end_handle)
					
		elif event == _IRQ_PERIPHERAL_DISCONNECT:
	     	# Connected peripheral has disconnected.
			conn_handle, addr_type, addr = data
			if WW_DEBUG: print('peripheral disconnected')
			self.addr_list.clear()
			self.scan()

		elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT:
			# Called for each characteristic found by gattc_discover_services().
			conn_handle, def_handle, value_handle, properties, uuid = data
			if conn_handle == self.server_conn_handle:
				if uuid == STATUS_UUID:
					self.cli_status_value_handle = value_handle
					if WW_DEBUG: print('discovered status char')
				elif uuid == DESIRED_SPEED_UUID:
					self.cli_speed_value_handle = value_handle
					if WW_DEBUG: print('discovered speed char')
				elif uuid == DIREX_UUID:
					self.cli_direx_value_handle = value_handle
					if WW_DEBUG: print('discovered direx char')
				elif uuid == RESET_UUID:
					self.cli_reset_value_handle = value_handle
					if WW_DEBUG: print('discovered reset char')
				if WW_DEBUG: print('characteristic result: ', conn_handle, ' ', def_handle, ' ', value_handle, ' ', properties, ' ', uuid)

		elif event == _IRQ_GATTC_CHARACTERISTIC_DONE:
			# Called once service discovery is complete.
			# Note: Status will be zero on success, implementation-specific value otherwise.
			conn_handle, status = data
			if WW_DEBUG: print('Characteristics discovered. PRESS ENTER to continue')
			return

		elif event == _IRQ_GATTC_WRITE_DONE:
			# A gattc_write() has completed.
			# Note: The value_handle will be zero on btstack (but present on NimBLE).
			# Note: Status will be zero on success, implementation-specific value otherwise.
			conn_handle, value_handle, status = data
			if WW_DEBUG: print('gatt client write complete: ', value_handle)

		elif event == _IRQ_GATTC_READ_RESULT:
			# A gattc_read() has completed.
			conn_handle, value_handle, char_data = data
			print('gattc read result')
			if conn_handle == self.server_conn_handle and value_handle == self.cli_speed_value_handle:
				print('data read:', char_data)

		elif event == _IRQ_GATTC_READ_DONE:
			# A gattc_read() has completed.
			# Note: The value_handle will be zero on btstack (but present on NimBLE).
			# Note: Status will be zero on success, implementation-specific value otherwise.
			conn_handle, value_handle, status = data
			print('gattc read done')

	def __get_info(self):
		mac = self.bl.config('mac')
		print('mac address = ', mac)
		gap = self.bl.config('gap_name')
		print('gap name = ', gap)
		rxb = self.bl.config('rxbuf')
		print('receive buffer size = ', rxb)

	def deInit(self):
		self.bl.active(False)

	def scan(self):
		self.bl.gap_scan()

	def getConnectionStatus(self):
		return self.connected
	
	def server_readDesiredSpeed(self):
		if self.is_server:
			ret = self.bl.gatts_read(self.serv_speed_value_handle)
			return int.from_bytes(ret, 'big')
		else:
			print('permission denied')

	def server_readMotorCharacteristic(self, key=None):
		if self.is_server:
			ret = self.bl.gatts_read(self.attr_handle_dict[key])
			#if WW_DEBUG: print('this is the data before decoding: ', ret)
			give = int.from_bytes(ret, 'big')
			#if WW_DEBUG: print('this is ret: ', give)
			return give
		else:
			print('permission denied')

	def client_writeSpeed(self, inpu):
		if self.is_server:
			print('permission denied')
		else:
			cmd_speed = inpu.to_bytes(1, 'big')
			self.bl.gattc_write(self.server_conn_handle, self.cli_speed_value_handle, cmd_speed, 1)

	def client_readSpeed(self):
		if self.is_server:
			print('permission denied')
		else:
			self.bl.gattc_read(self.server_conn_handle, self.cli_speed_value_handle)

	def client_writeStatus(self, motor_on=True):
		if self.is_server:
			print('permission denied')
		elif motor_on:
			self.bl.gattc_write(self.server_conn_handle, self.cli_status_value_handle, b'\x01', 1)
		else:
			self.bl.gattc_write(self.server_conn_handle, self.cli_status_value_handle, b'\x00', 1)

	#need to change the way this is interpreted by Server for fwd to actually work
	def client_writeDirex(self, fwd=True):
		if self.is_server:
			print('permission denied')
		elif fwd: #fwd = ccw
			self.bl.gattc_write(self.server_conn_handle, self.cli_direx_value_handle, b'\x01', 1)
		else:
			self.bl.gattc_write(self.server_conn_handle, self.cli_direx_value_handle, b'\x00', 1)

	def client_forceReset(self):
		if not self.is_server:
			#anything written to this attribute will force a reset
			self.bl.gattc_write(self.server_conn_handle, self.cli_reset_value_handle, b'\x00', 1)

	def __stopScan(self):
		self.bl.gap_scan(None)

	#BLE.gap_advertise(interval_us, adv_data=None, resp_data=None, connectable=True)
	#us_interval needs to be a really high number - look into this more
	def advertise(self, us_interval=40000, broadcast_data=b'\x66\x44\x33\x22', reply_data=b'\x55\x99\x33\x22', cnx=True):
		#add funcitonality to disable scan first
		self.bl.gap_advertise(interval_us=us_interval, adv_data=advEncodeName('WW Server'), resp_data=reply_data, connectable=cnx)
		# while True:
		# 	bl.irq(bt_irq)
		# 	utime.sleep_ms(10)

	def __stopAdvertising(self):
		self.bl.gap_advertise(interval_us=None)

	def __connect(self, address):
		self.bl.gap_connect(addr=address)

	# BLE.gap_connect(addr_type, addr, scan_duration_ms=2000, /)
	def __cnxToMyPC(self):
		self.bl.gap_connect(0, self.pier, 200000)

	def __decodeAddress(self, addr):
		i = 0
		while i < len(addr):
			hexa = hex(addr[i])
			print(hexa, end = ' ') 
			i += 1
		print('')

	def randomSpeedScript(self):
		self.client_writeStatus(False)
		utime.sleep_ms(50)
		self.client_writeSpeed(43)
		utime.sleep_ms(50)
		self.client_writeSpeed(30)
		utime.sleep_ms(50)
		self.client_writeDirex(False)
		utime.sleep_ms(50)
		self.client_writeSpeed(43)
		utime.sleep_ms(50)
		self.client_writeDirex(True)
		utime.sleep_ms(50)
		self.client_writeSpeed(30)
		utime.sleep_ms(50)
		self.client_writeDirex(False)
		utime.sleep_ms(50)
		self.client_writeSpeed(43)
		utime.sleep_ms(50)
		self.client_writeDirex(True)
		utime.sleep_ms(50)
		self.client_writeSpeed(30)		
		utime.sleep_ms(50)
		self.client_writeStatus(True)

#following three Encode methods taken form uPython forum

# @staticmethod
def advEncode(adv_type, value):
    return bytes((len(value) + 1, adv_type,)) + value

# @staticmethod
def advEncodeName(name):
    return advEncode(const(0x09), name.encode())

# @staticmethod
def advEncodeServiceData(data):
	return advEncode(const(0x16), data.encode())

# class connectable ble: - - - >>>make this a thing, its a good idea (don't just put adv data, put everything else)
	
# @staticmethod
def decodeAdvData(raw_adv_data):
	total_len = len(raw_adv_data)
	ind = 0
	while total_len > 0:
		sn_length = raw_adv_data[ind]
		ind += 1
		print('adv_length: ', sn_length)
		sn_type = raw_adv_data[ind]
		ind += 1
		print('adv_type: ', sn_type)
		sn_data = raw_adv_data[ind : sn_length+1]
		print('adv_data: ', sn_data)
		ind +=sn_length-1
		total_len -= (sn_length+1)
		print('-----------')



