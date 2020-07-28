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

Usage:
------



Hardware:
---------

#### Setup:
<img src="https://github.com/waleckaw/esp32_BLE_MotorControl/blob/master/media/IMG_8885.JPG" width="600" height="450" />


#### MCU - [esp32-WROOM-32D](https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32d_esp32-wroom-32u_datasheet_en.pdf)
<img src="https://github.com/waleckaw/esp32_BLE_MotorControl/blob/master/media/doit-esp-wroom-32-devkit.jpg" width="550" height="400" />


#### Motor - [25mm Geared Encoder Motor](https://forum.makeblock.com/t/information-about-25mm-dc-encoder-motor/10791)
<img src="https://github.com/waleckaw/esp32_BLE_MotorControl/blob/master/media/IMG_8888.JPG" width="600" height="450" />


#### Motor Driver - [SN754410 Quadruple Half-H Driver](https://www.ti.com/lit/ds/symlink/sn754410.pdf)
<img src="https://github.com/waleckaw/esp32_BLE_MotorControl/blob/master/media/h-bridge-sn754410.jpg" width="500" height="340" />





