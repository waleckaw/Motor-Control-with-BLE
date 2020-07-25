#esp32_BLE_MotorControl

Bluetooth Low Energy remote control for DC motor. Written in Python for 2x Espressif ESP32-WROOM-32 series MCU's running MicroPython build: ([**esp32-idf3-20200616-unstable-v1.12-538-gb4d0d7bf0.bin**](https://micropython.org/download/esp32/))

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

- setup

<!-- </br>
<img src="https://raw.githubusercontent.com/waleckaw/esp32_BLE_MotorControl/blob/master/media/IMG_8885.JPG" width="80%" height="80%" alt="X_Nucleo_IDB05A1_mbed_pinout_v1"/>
</br> -->

![alt text](/media/IMG_8885.JPG)

- ([esp32-WROOM-32D](https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32d_esp32-wroom-32u_datasheet_en.pdf))

<!-- </br>
<img src="https://raw.githubusercontent.com/waleckaw/esp32_BLE_MotorControl/blob/master/media/doit-esp-wroom-32-devkit.jpg" width="80%" height="80%" alt="X_Nucleo_IDB05A1_mbed_pinout_v1"/>
</br> -->

![alt text](/media/doit-esp-wroom-32-devkit.jpg)

- ([25mm geared encoder motor](https://forum.makeblock.com/t/information-about-25mm-dc-encoder-motor/10791))

<!-- </br>
<img src="https://raw.githubusercontent.com/waleckaw/esp32_BLE_MotorControl/blob/master/media/IMG_8888.JPG" width="80%" height="80%" alt="X_Nucleo_IDB05A1_mbed_pinout_v1"/>
</br> -->

![alt text](/media/IMG_8888.JPG)

- ([motor driver](https://www.ti.com/lit/ds/symlink/sn754410.pdf)) - SN754410 Quadruple Half-H Driver
https://www.ti.com/lit/ds/symlink/sn754410.pdf

<!-- </br>
<img src="https://raw.githubusercontent.com/waleckaw/esp32_BLE_MotorControl/blob/master/media/h-bridge-sn754410.jpg" width="80%" height="80%" alt="X_Nucleo_IDB05A1_mbed_pinout_v1"/>
</br> -->

![alt text](/media/h-bridge-sn754410.jpg)




