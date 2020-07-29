# BLE MotorControl

Bluetooth Low Energy remote control for DC motor. Written in Python for 2x Espressif ESP32-WROOM-32 series MCU's running MicroPython build: [**esp32-idf3-20200616-unstable-v1.12-538-gb4d0d7bf0.bin**](https://micropython.org/download/esp32/)

Demo:
-----

[![Alt text](https://img.youtube.com/vi/jWYvNjDsq4A/0.jpg)](https://www.youtube.com/watch?v=jWYvNjDsq4A)

Features:
---------

- Automatic device pairing + user API to script interactions with DC Motor or control directly from µPython REPL ([BLE_Class.py](https://github.com/waleckaw/esp32_BLE_MotorControl/blob/master/BLE_Class.py))
- PI motor control module ([MC_Class.py](https://github.com/waleckaw/esp32_BLE_MotorControl/blob/master/MC_Class.py))
- Flexible synchronous scheduler to manage multiple tasks ([WWsched.py](https://github.com/waleckaw/esp32_BLE_MotorControl/blob/master/WWsched.py))
- Central (client) BLE module can be used standalone as BLE discovery device to discover, display packet info, and connect to nearby advertising peripherals
- Peripheral also compatible with [Bluetility](https://github.com/jnross/Bluetility/releases) (Mac) + other BLE peripheral discovery/interaction platforms like [ST BLE Sensor for iOS/Android](https://www.st.com/en/embedded-software/stblesensor.html)

Installation:
------
- Download binary for esp32: [**esp32-idf3-20200616-unstable-v1.12-538-gb4d0d7bf0.bin**](https://micropython.org/download/esp32/)
- Load µPython onto Server esp32 board. See steps [here](https://learn.sparkfun.com/tutorials/how-to-load-micropython-on-a-microcontroller-board/esp32-thing)
- Install [ampy](https://learn.sparkfun.com/tutorials/micropython-programming-tutorial-getting-started-with-the-esp32-thing/setup) - tool for uploading µPython files to esp32 and other boards running micropython
- Clone this repo to your PC
- **Server**: upload relevant .py files to board using ampy
```bash
ampy --port **your port** put BLE_Class.py MC_Class.py BLEMCServer.py esp32_BLEProj_Server_boot/boot.py
```

- If using another esp32 as client (see Demo), edit your local BLEMCClient and esp32_BLEProj_Client_boot/boot.py to your desire then upload to your Client esp32 using
```bash
ampy --port <YOUR_PORT> put BLEMCClient.py esp32_BLEProj_Client_boot/boot.py
```
- Use terminal to access Client board, then use provided or custom libraries to control board

**--OR--**

- Download [Bluetility](https://github.com/jnross/Bluetility/releases) or another Third-Party BLE peripheral access interface
- BLE Characteristics Value Handle:
	- Status: 
		- UUID = dac11e24-ba93-11ea-b3de-0242ac130004
		- Hex: write 01 for active, 00 for disabled
	- Speed: 
		- UUID = a0ad58b2-b76c-11ea-b3de-0242ac130004
		- Hex: write any value between 1E and 46 (Decimal: 30 and 70) to control RPM
	- Direction: 
		- UUID = c6f75c74-ba88-11ea-b3de-0242ac130004
		- Hex: write 01 for CCW, 00 for CW (depending on your circuit)
	- Force Server Reset: 
		- UUID = 36ca78c0-ca32-11ea-87d0-0242ac130003
		- Hex: write 01 to reset


Setup:
---------

<img src="https://github.com/waleckaw/esp32_BLE_MotorControl/blob/master/media/IMG_8885.JPG" width="500" height="375" />

Schematic:
---------

<img src="https://github.com/waleckaw/esp32_BLE_MotorControl/blob/master/media/MC_BLE_schematic.png" width="600" height="350" />

Hardware:
---------

#### MCU - [esp32-WROOM-32D](https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32d_esp32-wroom-32u_datasheet_en.pdf) - Purchase [here](https://www.amazon.com/gp/product/B07Q576VWZ/ref=ppx_yo_dt_b_asin_title_o07_s00?ie=UTF8&psc=1)
<img src="https://github.com/waleckaw/esp32_BLE_MotorControl/blob/master/media/doit-esp-wroom-32-devkit.jpg" width="370" height="290" />


#### Motor - [25mm Geared Encoder Motor](https://forum.makeblock.com/t/information-about-25mm-dc-encoder-motor/10791)
<img src="https://github.com/waleckaw/esp32_BLE_MotorControl/blob/master/media/IMG_8888.JPG" width="400" height="300" />


#### Motor Driver - [SN754410 Quadruple Half-H Driver](https://www.ti.com/lit/ds/symlink/sn754410.pdf)
<img src="https://github.com/waleckaw/esp32_BLE_MotorControl/blob/master/media/h-bridge-sn754410.jpg" width="360" height="230" />





