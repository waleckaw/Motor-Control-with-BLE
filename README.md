Two esp32 dev boards running Micropython communicate via bluetooth. User inputs simple API commands to control attributes of BLE Service shared between Client (User) and Server (remote DC motor). These attributes determine the motor's on/off status, speed, and direction. Motor speed is held constant at desired speed using PID control loop
