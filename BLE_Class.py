# IMPORTANT:
# only compatible with certain unstable builds for esp32 that include ubluetooth
import ubluetooth
import utime
import struct
import utime

from micropython import const

# constants defining interrupt events from esp32 BLE module
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_SCAN_RESULT = const(5)
_IRQ_PERIPHERAL_CONNECT = const(7)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTC_SERVICE_RESULT = const(9)
_IRQ_GATTC_CHARACTERISTIC_RESULT = const(11)
_IRQ_GATTC_CHARACTERISTIC_DONE = const(12)
_IRQ_GATTC_READ_RESULT = const(15)
_IRQ_GATTC_READ_DONE = const(16)
_IRQ_GATTC_WRITE_DONE = const(17)

# toggle debug print statements - should always be enabled (1) if in client mode
WW_DEBUG = const(1)

# used to output scan results to terminal
adv_type_dict = {0x00: 'ADV_IND - connectable and scannable undirected advertising',
0x01: 'ADV_DIRECT_IND - connectable directed advertising',
0x02: 'ADV_SCAN_IND - scannable undirected advertising',
0x03: 'ADV_NONCONN_IND - non-connectable undirected advertising',
0x04: 'SCAN_RSP - scan response'}

# device MAC address - only server addr required for connection. can be discovered using __get_info
_SERVER_ADDR = b'$b\xab\xf9\x0bR'
_CLIENT_ADDR = b'$b\xab\xf9\x17\xd6'

#attribute indicators
BLE_ATTR_STATUS = const(0)
BLE_ATTR_SPEED = const(1)
BLE_ATTR_DIREX = const(2)
BLE_ATTR_RESET = const(3)

# V1 UUID's below generated using: https://www.uuidgenerator.net
# Bluetooth UUID of motor control service
CUSTOM_MOTOR_CONTROL_SERVICE_UUID = ubluetooth.UUID('1ab35ef6-b76b-11ea-b3de-0242ac130004')
# Bluetooth characteristic UUID, properties
STATUS_UUID = ubluetooth.UUID('dac11e24-ba93-11ea-b3de-0242ac130004')
CUSTOM_STATUS_CHAR = (STATUS_UUID, ubluetooth.FLAG_WRITE | ubluetooth.FLAG_READ,)
DESIRED_SPEED_UUID = ubluetooth.UUID('a0ad58b2-b76c-11ea-b3de-0242ac130004')
CUSTOM_DESIRED_SPEED_CHAR = (DESIRED_SPEED_UUID, ubluetooth.FLAG_WRITE | ubluetooth.FLAG_READ,)
DIREX_UUID = ubluetooth.UUID('c6f75c74-ba88-11ea-b3de-0242ac130004')
CUSTOM_DESIRED_DIREX_CHAR = (DIREX_UUID, ubluetooth.FLAG_WRITE | ubluetooth.FLAG_READ,)
RESET_UUID = ubluetooth.UUID('36ca78c0-ca32-11ea-87d0-0242ac130003')
CUSTOM_DESIRED_RESET_CHAR = (RESET_UUID, ubluetooth.FLAG_WRITE)

# full definition of service
CUSTOM_MOTOR_CONTROL_SERVICE = (CUSTOM_MOTOR_CONTROL_SERVICE_UUID, (CUSTOM_STATUS_CHAR, CUSTOM_DESIRED_SPEED_CHAR, CUSTOM_DESIRED_DIREX_CHAR, CUSTOM_DESIRED_RESET_CHAR,),)
SERVICE_LIST = (CUSTOM_MOTOR_CONTROL_SERVICE,)

# class used to operate BLE and send commands to motor controller (client) or receive 
# commands and indicate them to motor controller (Server)
class mc_BLE:

	# initiallize BLE for MC - attributes include list of discovered devices (MAC addresses), pier 
	# address of desired server, BLE obj from ubluetooth library, connection status, role as server/client
	# attribute update dictionary (if server), and attrivute handles (if server)
	def __init__(self, pier_addr=_SERVER_ADDR, server_role=False):
		self.addr_list = []
		self.pier = pier_addr
		self.bl = ubluetooth.BLE()
		self.bl.active(True)
		self.bl.irq(handler=self.bt_irq)
		self.connected = False
		self.is_server=server_role
		if server_role:
			self.update_ready=False
			self.attr_update_dict = {BLE_ATTR_STATUS: 0, BLE_ATTR_SPEED: 0, BLE_ATTR_DIREX: 0, BLE_ATTR_RESET: 0}
		self.__get_info()

		if server_role:
			# here, serv_ refers to server, not service
			((self.serv_status_value_handle, self.serv_speed_value_handle, self.serv_direx_value_handle, self.serv_reset_value_handle),) = self.bl.gatts_register_services(SERVICE_LIST)
			self.attr_handle_dict = {BLE_ATTR_STATUS: self.serv_status_value_handle, BLE_ATTR_SPEED: self.serv_speed_value_handle, BLE_ATTR_DIREX: self.serv_direx_value_handle, BLE_ATTR_RESET: self.serv_reset_value_handle}
			# peripheral (in this case, server) will advertise indefinitely until discovered by desired central
			self.advertise()
		else:
			# central (in this case, client) will scan indefinitely until it discovers desired peripheral
			self.scan()

	# bt_irq handles interrupts from BLE.irq with specific BLE event and data input
	# that it assigns to to variables (ie: conn_handle, addr_type, addr, attr handle, etc)
	# once desired pier address (defined by _SERVER_ADDR above) is discovered, automatic connection follows this
	# sequence: scan -> connect -> discover MC Service -> discover MC Service characteristics -> register characteristic handles
	# characteristic attr handles/connection complete
	# above process performed by Central/Client if multiple BLE devices are used
	def bt_irq(self, event, data):

		# A central has connected to this peripheral - update connection status
		if event == _IRQ_CENTRAL_CONNECT:
			if WW_DEBUG: print('connection from central');
			self.connected = True

		# A central has disconnected from this peripheral (in this case, server) - resume 
		# advertising to reconnect to central (client) when available
		elif event == _IRQ_CENTRAL_DISCONNECT:
			self.connected = False
			self.advertise()

		# A central has written to this characteristic - change correspoding entry in
		# attr_update_dict to 1 (used by event-checker in BLEMCServer)
		elif event == _IRQ_GATTS_WRITE:
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

		# central has discovered a peripheral during scan - if peripheral's addr matches desired 
		# pier addr (that of the BLEMCServer), connect to peripheral and stop scanning
		elif event == _IRQ_SCAN_RESULT:
			addr_type, addr, adv_type, rssi, adv_data = data
			new_addr = bytes(addr)
			if addr == self.pier:
				self.__connectToServer()
				self.__stopScan()
			elif new_addr not in self.addr_list:
				self.addr_list.append(new_addr)
				print('Device discovered. addr_type = ', addr_type, 'addr = ', addr, 'adv_type = ', adv_type, ': ', adv_type_dict[adv_type], 'adv_data = ', adv_data)
				self.__decodeAddress(addr)
				decodeAdvData(adv_data)

		# connection established with peripheral - update server class attribute server_conn_handle 
		# and discover services present
		elif event == _IRQ_PERIPHERAL_CONNECT:
			self.server_conn_handle, addr_type, addr = data
			print('peripheral connect')
			self.bl.gattc_discover_services(self.server_conn_handle)

		# connection to peripheral lost - resume scan until desired peripheral comes back online/in range
		elif event == _IRQ_PERIPHERAL_DISCONNECT:
			# conn_handle, addr_type, addr = data #RECENTLY COMMENTED OUT TO TEST
			if WW_DEBUG: print('peripheral disconnected')
			self.addr_list.clear()
			self.scan()

		# central has discovered a service of paired peripheral - discover service characteristics
		elif event == _IRQ_GATTC_SERVICE_RESULT:
			conn_handle, start_handle, end_handle, uuid = data
			if conn_handle == self.server_conn_handle and uuid == CUSTOM_MOTOR_CONTROL_SERVICE_UUID:
				self.bl.gattc_discover_characteristics(self.server_conn_handle, start_handle, end_handle)

		# central has discovered a service characteristic of paired peripheral - depending on
		# characteristic UUID, record characteristic value handle for future client write operations
		elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT:
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

		# discovery of service characteristics complete. Prompt user (client side) to begin writing values
		elif event == _IRQ_GATTC_CHARACTERISTIC_DONE:
			if WW_DEBUG: print('Characteristics discovered. PRESS ENTER to continue')

		# read of characteristic data complete - print to screen
		elif event == _IRQ_GATTC_READ_RESULT:
			conn_handle, value_handle, char_data = data
			if conn_handle == self.server_conn_handle:
				int_data = int.from_bytes(char_data, 'big')
				if WW_DEBUG: print('data read from server:', int_data)

		# client write to server characteristic complete
		elif event == _IRQ_GATTC_WRITE_DONE:
			conn_handle, value_handle, status = data
			if value_handle == self.cli_status_value_handle:
				if WW_DEBUG: print('client write status complete')
			elif value_handle == self.cli_speed_value_handle:
				if WW_DEBUG: print('client write speed complete')
			elif value_handle == self.cli_direx_value_handle:
				if WW_DEBUG: print('client write direction complete')

	# prints basic info about the BLE device to terminal
	def __get_info(self):
		mac = self.bl.config('mac')
		print('mac address = ', mac)
		gap = self.bl.config('gap_name')
		print('gap name = ', gap)
		rxb = self.bl.config('rxbuf')
		print('receive buffer size = ', rxb)

	# initializes GAP scan for BLE peripheral devices
	def scan(self):
		self.bl.gap_scan()

	# returns connected status - for use by server event checker
	def getConnectionStatus(self):
		return self.connected
	
	# allows server to read motor characteristics once updated
	def server_readMotorCharacteristic(self, key=None):
		if self.is_server:
			ret = self.bl.gatts_read(self.attr_handle_dict[key])
			give = int.from_bytes(ret, 'big')
			return give
		else:
			print('permission denied')

	# used to initialize server FWD direction as 1
	def server_singleWriteDirexFWD(self):
		self.bl.gatts_write(self.serv_direx_value_handle, b'\x01')

	# client API command to write speed - takes integer between 30 and 70 (RPM)
	def client_writeSpeed(self, inpu):
		if self.is_server:
			print('permission denied')
		else:
			cmd_speed = inpu.to_bytes(1, 'big')
			self.bl.gattc_write(self.server_conn_handle, self.cli_speed_value_handle, cmd_speed, 1)

	# client API command to read current value of server speed characteristic 
	def client_readSpeed(self):
		if self.is_server:
			print('permission denied')
		else:
			self.bl.gattc_read(self.server_conn_handle, self.cli_speed_value_handle)

	# client API command to turn motor on or off
	def client_writeStatus(self, motor_on=True):
		if self.is_server:
			print('permission denied')
		elif motor_on:
			cmd_stat = b'\x01'
		else:
			cmd_stat = b'\x00'
		self.bl.gattc_write(self.server_conn_handle, self.cli_status_value_handle, cmd_stat, 1)

	# client API command to read whether motor is on or off
	def client_readStatus(self):
		if self.is_server:
			print('permission denied')
		else:
			self.bl.gattc_read(self.server_conn_handle, self.cli_status_value_handle)

	# client API command to write Motor Direction (FWD = 1, BCK = 0) - initialized on server as 1
	# so that motor starts FWD. CCW vs CW will depend on user circuit
	def client_writeDirex(self, fwd=True):
		if self.is_server:
			print('permission denied')
		elif fwd:
			cmd_direx = b'\x01'
		else:
			cmd_direx = b'\x00'
		self.bl.gattc_write(self.server_conn_handle, self.cli_direx_value_handle, cmd_direx, 1)

	# client API command to read whether motor is going FWD (1) of BCK (0)
	# CCW vs CW will depend on user circuit
	def client_readDirex(self):
		if self.is_server:
			print('permission denied')
		else:
			self.bl.gattc_read(self.server_conn_handle, self.cli_direx_value_handle)

	# client API command to force reset on Server
	def client_forceReset(self):
		if not self.is_server:
			#anything written to this attribute will force a reset
			self.bl.gattc_write(self.server_conn_handle, self.cli_reset_value_handle, b'\x00', 1)

	# internal method to stop scan - not meant for use in terminal by client
	def __stopScan(self):
		self.bl.gap_scan(None)

	# figure out if reply data even necessary
	def advertise(self, reply_data=b'\x55\x99\x33\x22'):
		self.bl.gap_advertise(interval_us=40000, adv_data=advEncodeName('WW Server'), resp_data=reply_data, connectable=True)

	# internal method that stops peripheral (Server) from advertising
	def __stopAdvertising(self):
		self.bl.gap_advertise(interval_us=None)

	# # internal method that connects BLE central to peripheral with given address
	# def __connect(self, address):
	# 	self.bl.gap_connect(addr=address)

	# internal method that connects BLE central to peripheral - to be called after discovery of
	# desired peripheral
	def __connectToServer(self):
		self.bl.gap_connect(0, self.pier, 200000)

	# FIGURE OUT IF YOU NEED CONNECT AND CONNECTTOSERVER
	def __decodeAddress(self, addr):
		i = 0
		while i < len(addr):
			hexa = hex(addr[i])
			print(hexa, end = ' ') 
			i += 1
		print('')

	def randomSpeedScript(self):
		if self.is_server:
			pass
		else:
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

	def __del__(self):
		self.bl.active(False)

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



