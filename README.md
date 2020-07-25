#esp32_BLE_MotorControl

Bluetooth Low Energy remote control for DC motor. Written in Python for ESP32-WROOM-32 series MCU's running micropython build: 

Features:
---------

- Parsing and Building of HCI packets
- Allows PyBoard to control BLE chips using HCI packets

Usage:
------

Two esp32 dev boards running Micropython communicate via bluetooth. User inputs simple API commands to control attributes of BLE Service shared between Client (User) and Server (remote DC motor). These attributes determine the motor's on/off status, speed, and direction. Motor speed is held constant (subject to motor torque capabilities) at desired speed using PID control loop
