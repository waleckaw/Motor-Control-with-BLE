#esp32_BLE_MotorControl

Bluetooth Low Energy remote control for DC motor. Written in Python for 2x Espressif ESP32-WROOM-32 series MCU's running MicroPython build: **esp32-idf3-20200616-unstable-v1.12-538-gb4d0d7bf0.bin**
which can be downloaded here: https://micropython.org/download/esp32/ at the time of creation of this document (7/24/20)

Demo:
-----
[insert video]

Features:
---------

- Automatic device pairing + user API to script interactions with DC Motor or control directly from µPython REPL ([BLE_Class.py](https://github.com/waleckaw/esp32_BLE_MotorControl/blob/master/BLE_Class.py))
- PI motor control module ([MC_Class.py](https://github.com/waleckaw/esp32_BLE_MotorControl/blob/master/MC_Class.py))
- Flexible synchronous scheduler to manage multiple tasks ([WWsched.py](https://github.com/waleckaw/esp32_BLE_MotorControl/blob/master/WWsched.py))
- Central (client) BLE module can be used standalone as BLE discovery device to discover, display packet info, and connect to nearby advertising peripherals
- Peripheral also compatible with [Bluetility](https://github.com/jnross/Bluetility/releases) (Mac) + other BLE peripheral discovery/interaction platforms like [ST BLE Sensor for iOS/Android](https://www.st.com/en/embedded-software/stblesensor.html)

Hardware:
---------

add links to photo of:
- setup
- esp32
- motor
- motor driver 

