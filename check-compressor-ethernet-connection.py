from time import sleep
from gpiozero import Button, LED, PWMOutputDevice
from pymodbus.client import ModbusTcpClient
import numpy as np
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.exceptions import InfluxDBError
from dotenv import load_dotenv
import os

load_dotenv()

boris = ModbusTcpClient(
    "192.168.1.2", port=502
)  # this IP is enforced on BORIS compressor
boris.connect()

sylvia = ModbusTcpClient(
    "192.168.0.2", port=502
)  # this IP is enforced on SYLVIA compressor
sylvia.connect()

if not boris.connected:
    print("Modbus error: Boris compressor ethernet connection is lost.")
if not sylvia.connected:
    print("Modbus error: Sylvia compressor ethernet connection is lost.")

# reading compressor state
if boris.connected:
    boris_register = (boris.read_input_registers(address=1))
    if boris_register.isError():
        print("Modbus error for Boris compressor state register:", result)
if sylvia.connected:
    sylvia_register = (boris.read_input_registers(address=1))
    if sylvia_register.isError():
        print("Modbus error for Sylvia compressor state register:", result)

# reading oil temperature
if boris.connected:
    boris_register = (boris.read_input_registers(address=42))
    if boris_register.isError():
        print("Modbus error for Boris oil temperature register:", result)
if sylvia.connected:
    sylvia_register = (boris.read_input_registers(address=42))
    if sylvia_register.isError():
        print("Modbus error for Sylvia oil temperature register:", result)