# IMPORTANT:
# only compatible with certain unstable builds for esp32 that include ubluetooth
import ubluetooth
import utime
import struct
import utime
import ubinascii

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
_WW_DEBUG = const(1)

# used to output scan results to terminal
adv_type_dict = {0x00: 'ADV_IND - connectable and scannable undirected advertising',
0x01: 'ADV_DIRECT_IND - connectable directed advertising',
0x02: 'ADV_SCAN_IND - scannable undirected advertising',
0x03: 'ADV_NONCONN_IND - non-connectable undirected advertising',
0x04: 'SCAN_RSP - scan response'}

#attribute indicators
BLE_ATTR_STATUS = const(0)
BLE_ATTR_SPEED = const(1)
BLE_ATTR_DIREX = const(2)
BLE_ATTR_RESET = const(3)

# V1 UUID's below generated using: https://www.uuidgenerator.net
# Bluetooth UUID of motor control service
_CUSTOM_MOTOR_CONTROL_SERVICE_UUID = ubluetooth.UUID('1ab35ef6-b76b-11ea-b3de-0242ac130004')
# Bluetooth characteristic UUID, properties
_STATUS_UUID = ubluetooth.UUID('dac11e24-ba93-11ea-b3de-0242ac130004')
_CUSTOM_STATUS_CHAR = (_STATUS_UUID, ubluetooth.FLAG_WRITE | ubluetooth.FLAG_READ,)
_DESIRED_SPEED_UUID = ubluetooth.UUID('a0ad58b2-b76c-11ea-b3de-0242ac130004')
_CUSTOM_DESIRED_SPEED_CHAR = (_DESIRED_SPEED_UUID, ubluetooth.FLAG_WRITE | ubluetooth.FLAG_READ,)
_DIREX_UUID = ubluetooth.UUID('c6f75c74-ba88-11ea-b3de-0242ac130004')
_CUSTOM_DESIRED_DIREX_CHAR = (_DIREX_UUID, ubluetooth.FLAG_WRITE | ubluetooth.FLAG_READ,)
_RESET_UUID = ubluetooth.UUID('36ca78c0-ca32-11ea-87d0-0242ac130003')
_CUSTOM_DESIRED_RESET_CHAR = (_RESET_UUID, ubluetooth.FLAG_WRITE)

# full definition of service
_CUSTOM_MOTOR_CONTROL_SERVICE = (_CUSTOM_MOTOR_CONTROL_SERVICE_UUID, (_CUSTOM_STATUS_CHAR, _CUSTOM_DESIRED_SPEED_CHAR, _CUSTOM_DESIRED_DIREX_CHAR, _CUSTOM_DESIRED_RESET_CHAR,),)
_SERVICE_LIST = (_CUSTOM_MOTOR_CONTROL_SERVICE,)

# class used to operate BLE and send commands to motor controller (client) or receive 
# commands and indicate them to motor controller (Server)
class mc_BLE:

	# initiallize BLE for MC - attributes include list of discovered devices (MAC addresses), pier 
	# address of desired server, BLE obj from ubluetooth library, connection status, role as server/client
	# attribute update dictionary (if server), and attrivute handles (if server)
	def __init__(self, server_role=False):
		self._addr_list = []
		self._pier = None
		self._bl = ubluetooth.BLE()
		self._bl.active(True)
		self._bl.irq(handler=self._bt_irq)
		self._connected = False
		self._is_server=server_role
		if server_role:
			self._update_ready=False
			self._attr_update_dict = {BLE_ATTR_STATUS: 0, BLE_ATTR_SPEED: 0, BLE_ATTR_DIREX: 0, BLE_ATTR_RESET: 0}
		self.get_info()

		if server_role:
			# here, serv_ refers to server, not service
			((self._server_status_value_handle, self._server_speed_value_handle, self._server_direx_value_handle, self._server_reset_value_handle),) = self._bl.gatts_register_services(_SERVICE_LIST)
			self._attr_handle_dict = {BLE_ATTR_STATUS: self._server_status_value_handle, BLE_ATTR_SPEED: self._server_speed_value_handle, BLE_ATTR_DIREX: self._server_direx_value_handle, BLE_ATTR_RESET: self._server_reset_value_handle}
			# peripheral (in this case, server) will advertise indefinitely until discovered by desired central
			self.server_advertise()
		else:
			# central (in this case, client) will scan indefinitely until it discovers desired peripheral
			self.client_scan()

	# bt_irq handles interrupts from BLE.irq with specific BLE event and data input
	# that it assigns to to variables (ie: conn_handle, addr_type, addr, attr handle, etc)
	# once pier with correct adv data key is discovered is discovered, automatic connection follows sequence below
	# scan -> connect -> discover MC Service -> discover MC Service characteristics -> register characteristic handles
	# characteristic attr handles/connection complete
	# above process performed by Central/Client if multiple BLE devices are used
	def _bt_irq(self, event, data):

		# A central has connected to this peripheral - update connection status
		if event == _IRQ_CENTRAL_CONNECT:
			if _WW_DEBUG: print('connection from central')
			self._connected = True
			self.server_stop_advertising()

		# A central has disconnected from this peripheral (in this case, server) - resume 
		# advertising to reconnect to central (client) when available
		elif event == _IRQ_CENTRAL_DISCONNECT:
			self._connected = False
			self.server_advertise()

		# A central has written to this characteristic - change correspoding entry in
		# attr_update_dict to 1 (used by event-checker in BLEMCServer)
		elif event == _IRQ_GATTS_WRITE:
			if _WW_DEBUG: print('central has written')
			self._update_ready = True
			conn_handle, attr_handle = data
			if attr_handle == self._server_status_value_handle:
				self._attr_update_dict[BLE_ATTR_STATUS] = 1
			elif attr_handle == self._server_speed_value_handle:
				self._attr_update_dict[BLE_ATTR_SPEED] = 1
			elif attr_handle == self._server_direx_value_handle:
				self._attr_update_dict[BLE_ATTR_DIREX] = 1
			elif attr_handle == self._server_reset_value_handle:
				self._attr_update_dict[BLE_ATTR_RESET] = 1

		# central has discovered a peripheral during scan - if peripheral's addr matches desired 
		# pier addr (that of the BLEMCServer), connect to peripheral and stop scanning
		elif event == _IRQ_SCAN_RESULT:
			addr_type, addr, adv_type, rssi, adv_data = data
			new_addr = bytes(addr) # copy to use outside of interrupt
			if new_addr not in self._addr_list:
				self._addr_list.append(new_addr)
				print('Device discovered. addr_type = ', addr_type, 'addr = ', addr, 'adv_type = ', adv_type, ': ', adv_type_dict[adv_type], 'adv_data = ', adv_data)
				_print_as_readable_hex(adv_data)
				_decodeAddress(addr)
			if _decode_adv_data_for_key(bytes(adv_data)):
				self._pier = addr
				self._client_autoconnect_to_server()
				self.client_stop_scan()

		# connection established with peripheral - update server class attribute server_conn_handle 
		# and discover services present
		elif event == _IRQ_PERIPHERAL_CONNECT:
			self._server_conn_handle, addr_type, addr = data
			if _WW_DEBUG: print('peripheral connect')
			self._connected = True
			self._bl.gattc_discover_services(self._server_conn_handle)

		# connection to peripheral lost - resume scan until desired peripheral comes back online/in range
		elif event == _IRQ_PERIPHERAL_DISCONNECT:
			# conn_handle, addr_type, addr = data #RECENTLY COMMENTED OUT TO TEST
			if _WW_DEBUG: print('peripheral disconnected')
			self._addr_list.clear()
			self._connected = False
			self.client_scan()

		# central has discovered a service of paired peripheral - discover service characteristics
		elif event == _IRQ_GATTC_SERVICE_RESULT:
			conn_handle, start_handle, end_handle, uuid = data
			if conn_handle == self._server_conn_handle and uuid == _CUSTOM_MOTOR_CONTROL_SERVICE_UUID:
				self._bl.gattc_discover_characteristics(self._server_conn_handle, start_handle, end_handle)

		# central has discovered a service characteristic of paired peripheral - depending on
		# characteristic UUID, record characteristic value handle for future client write operations
		elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT:
			conn_handle, def_handle, value_handle, properties, uuid = data
			if conn_handle == self._server_conn_handle:
				if uuid == _STATUS_UUID:
					self.cli_status_value_handle = value_handle
					if _WW_DEBUG: print('discovered status char')
				elif uuid == _DESIRED_SPEED_UUID:
					self.cli_speed_value_handle = value_handle
					if _WW_DEBUG: print('discovered speed char')
				elif uuid == _DIREX_UUID:
					self.cli_direx_value_handle = value_handle
					if _WW_DEBUG: print('discovered direx char')
				elif uuid == _RESET_UUID:
					self.cli_reset_value_handle = value_handle
					if _WW_DEBUG: print('discovered reset char')

		# discovery of service characteristics complete. Prompt user (client side) to begin writing values
		elif event == _IRQ_GATTC_CHARACTERISTIC_DONE:
			if _WW_DEBUG: print('Characteristics discovered. PRESS ENTER to continue')

		# read of characteristic data complete - print to screen
		elif event == _IRQ_GATTC_READ_RESULT:
			conn_handle, value_handle, char_data = data
			if conn_handle == self._server_conn_handle:
				int_data = int.from_bytes(char_data, 'big')
				if _WW_DEBUG: print('data read from server:', int_data)

		# client write to server characteristic complete
		elif event == _IRQ_GATTC_WRITE_DONE:
			conn_handle, value_handle, status = data
			if value_handle == self.cli_status_value_handle:
				if _WW_DEBUG: print('client write status complete')
			elif value_handle == self.cli_speed_value_handle:
				if _WW_DEBUG: print('client write speed complete')
			elif value_handle == self.cli_direx_value_handle:
				if _WW_DEBUG: print('client write direction complete')

	# prints basic info about the BLE device to terminal
	def get_info(self):
		mac = self._bl.config('mac')
		print('mac address = ', mac)
		gap = self._bl.config('gap_name')
		print('gap name = ', gap)
		rxb = self._bl.config('rxbuf')
		print('receive buffer size = ', rxb)

	# initializes GAP scan for BLE peripheral devices
	def client_scan(self):
		if not self._is_server:
			self._bl.gap_scan()
		else:
			if _WW_DEBUG: print('permission denied')

	# returns connected status - for use by server event checker
	def cli_serv_get_connection_status(self):
		return self._connected
	
	# allows server to read motor characteristics once updated
	def server_read_motor_characteristic(self, key=None):
		if self._is_server:
			ret = self._bl.gatts_read(self._attr_handle_dict[key])
			give = int.from_bytes(ret, 'big')
			return give
		else:
			print('permission denied')

	# used to initialize server FWD direction as 1
	def server_init_direx(self):
		self._bl.gatts_write(self._server_direx_value_handle, b'\x01')

	# client API command to write speed - takes integer between 30 and 70 (RPM)
	def client_write_speed(self, inpu):
		if self._is_server:
			print('permission denied')
		else:
			cmd_speed = inpu.to_bytes(1, 'big')
			self._bl.gattc_write(self._server_conn_handle, self.cli_speed_value_handle, cmd_speed, 1)

	# client API command to read current value of server speed characteristic 
	def client_read_speed(self):
		if self._is_server:
			print('permission denied')
		else:
			self._bl.gattc_read(self._server_conn_handle, self.cli_speed_value_handle)

	# client API command to turn motor on or off
	def client_write_status(self, motor_on=True):
		if self._is_server:
			print('permission denied')
		elif motor_on:
			cmd_stat = b'\x01'
		else:
			cmd_stat = b'\x00'
		self._bl.gattc_write(self._server_conn_handle, self.cli_status_value_handle, cmd_stat, 1)

	# client API command to read whether motor is on or off
	def client_read_status(self):
		if self._is_server:
			print('permission denied')
		else:
			self._bl.gattc_read(self._server_conn_handle, self.cli_status_value_handle)

	# client API command to write Motor Direction (FWD = 1, BCK = 0) - initialized on server as 1
	# so that motor starts FWD. CCW vs CW will depend on user circuit
	def client_write_direx(self, fwd=True):
		if self._is_server:
			print('permission denied')
		elif fwd:
			cmd_direx = b'\x01'
		else:
			cmd_direx = b'\x00'
		self._bl.gattc_write(self._server_conn_handle, self.cli_direx_value_handle, cmd_direx, 1)

	# client API command to read whether motor is going FWD (1) of BCK (0)
	# CCW vs CW will depend on user circuit
	def client_read_direx(self):
		if self._is_server:
			print('permission denied')
		else:
			self._bl.gattc_read(self._server_conn_handle, self.cli_direx_value_handle)

	# client API command to force reset on Server
	def client_force_server_reset(self):
		if not self._is_server:
			#anything written to this attribute will force a reset
			self._bl.gattc_write(self._server_conn_handle, self.cli_reset_value_handle, b'\x00', 1)

	# internal method to stop scan
	def client_stop_scan(self):
		self._bl.gap_scan(None)

	# API that causes BLE module to advertise - using ubluetooth lib, this locks it into server
	# role once connection is made
	def server_advertise(self):
		self._bl.gap_advertise(interval_us=40000, adv_data=_adv_encode_name('MC Server'), connectable=True)

	# internal method that stops peripheral (Server) from advertising
	def server_stop_advertising(self):
		self._bl.gap_advertise(interval_us=None)

	# internal method that connects BLE central to peripheral - to be called after discovery of
	# desired peripheral
	def _client_autoconnect_to_server(self):
		self._bl.gap_connect(0, self._pier, 200000)

	# deactivate BLE upon deletion
	def de_init(self):
		if self._is_server:
			self.server_stop_advertising()
		else:
			self.client_stop_scan()
		self._bl.active(False)

	def __del__(self):
		self.de_init()

# encode data into BLE advertising packet format
def adv_encode(adv_type, value):
    return bytes((len(value) + 1, adv_type,)) + value

# encode name (str) as adv advertising packet
def _adv_encode_name(name):
    return adv_encode(const(0x09), name.encode())

# print string of hex/ascii as sepated hex bytes
def _print_as_readable_hex(data):
	i = 0
	while i < len(data):
		hexa = hex(data[i])
		print(hexa, end = ' ') 
		i += 1
	print('')

# print BLE mac address as sequence of hex bytes
def _decodeAddress(addr):
	print('-----------')
	print('address in hex:')
	_print_as_readable_hex(addr)
	print('-----------')
	
# separate and print length/type/value of BLE advertising data packets from discovered devices
def _decode_adv_data_for_key(raw_adv_data):
	print('discovered adv data:')
	total_len = len(raw_adv_data)
	ind = 0
	while total_len > 0:
		sn_length = raw_adv_data[ind]
		ind += 1
		print('adv_length: ', sn_length)
		sn_type = raw_adv_data[ind]
		ind += 1
		print('adv_type: ', sn_type)
		sn_data = raw_adv_data[ind : ind + sn_length+1]
		print('adv_data chunk: ', sn_data)
		print('adv_data chunk hex: ', end = ' ') 
		_print_as_readable_hex(sn_data)
		ind +=sn_length-1
		total_len -= (sn_length+1)
		print('-----------')
		# adv name chunk usually comes at end of adv data packet, so this shouldn't cut anything off
		if sn_data == b'MC Server':
			return True



