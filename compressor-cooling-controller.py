from time import sleep
from gpiozero import Button, LED, PWMOutputDevice
from pymodbus.client import ModbusTcpClient
import numpy as np

BORIS = ModbusTcpClient("192.168.1.2", port=502) # this IP is enforced on BORIS compressor
BORIS.connect()

SYLVIA = ModbusTcpClient("192.168.0.2", port=502) # this IP is enforced on SYLVIA compressor
SYLVIA.connect()

PIN_VALVE_CONTROL = 14 # pin that is connected to transistor
output_valve_control = LED(PIN_VALVE_CONTROL)

OIL_TEMP_THRESHOLD = 321 # x10 Celcius
COMPRESSOR_ON = 0x001
COMPRESSOR_OFF = 0x00FF

if 1:
    # compressors off
    BORIS.write_register(address=1, value=COMPRESSOR_OFF)
    SYLVIA.write_register(address=1, value=COMPRESSOR_OFF)

    # switch to cold water loop
    output_valve_control.on()
    sleep(105) # time it takes for valves to rotate from Eau de Ville to Cold loop

    # compressors back on
    BORIS.write_register(address=1, value=COMPRESSOR_ON)
    SYLVIA.write_register(address=1, value=COMPRESSOR_ON)
    sleep(10)

#output_valve_control.off()

while True:
    # are the compressors ON ? 
    _boris_state = (BORIS.read_input_registers(address=1)).registers[0]
    _sylvia_state = (SYLVIA.read_input_registers(address=1)).registers[0]

    _boris_oil_temp = (BORIS.read_input_registers(address=42)).registers[0]
    _sylvia_oil_temp = (SYLVIA.read_input_registers(address=42)).registers[0]

    if _boris_state == 3: # 3 means running
        if _boris_oil_temp > OIL_TEMP_THRESHOLD:
            output_valve_control.off() # switch to running water

    if _sylvia_state == 3:
        if _sylvia_oil_temp > OIL_TEMP_THRESHOLD:
            output_valve_control.off()

    sleep(1)

#output_valve_control.off()
