# Sensor Data Logger

## About
This utility translates usb mic audio into vibration data and sends it as mqtt messages. It can also read any sensor data from say `gpio` and include it in messages. Background noise cancelling can be done by adding a second mic located further from monitored and subtracting its readings. Source code acts as further documentation.

## Requirements
* Raspberry Pi
* USB mic

## Note for nodered users
Robust workflows can be created in `nodered` to process incoming `mqtt` messages and log these into a db. E.g. logging to a remote `mongodb` over an `autossh` tunnel.