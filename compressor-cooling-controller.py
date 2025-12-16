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

STATE_RUNNING_CODE = 3  # 3 means running

INFLUXDB_URL = "https://monitoring-quantic.phys.ens.fr:9086"
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = "quantic"  # Remplacer par votre organisation
INFLUXDB_BUCKET = "compressors"

try:
    influx_client = InfluxDBClient(
        url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG
    )
    write_api = influx_client.write_api(write_options=SYNCHRONOUS)
    print("Successfully connected to InfluxDB.")
except Exception as e:
    print(f"Error connecting to InfluxDB: {e}")
    write_api = None


PIN_VALVE_CONTROL = 14  # pin that is connected to transistor
output_valve_control = LED(PIN_VALVE_CONTROL)

OIL_TEMP_THRESHOLD = 260  # x10 Celcius
COMPRESSOR_ON = 0x001
COMPRESSOR_OFF = 0x00FF


boris = ModbusTcpClient(
    "192.168.1.2", port=502
)  # this IP is enforced on BORIS compressor
boris.connect()

sylvia = ModbusTcpClient(
    "192.168.0.2", port=502
)  # this IP is enforced on SYLVIA compressor
sylvia.connect()

go_to_cold_loop = False
#output_valve_control.on()

if go_to_cold_loop:
    # compressors off
    boris.write_register(address=1, value=COMPRESSOR_OFF)
    sylvia.write_register(address=1, value=COMPRESSOR_OFF)

    # switch to cold water loop
    output_valve_control.on()
    sleep(105)  # time it takes for valves to rotate from Eau de Ville to Cold loop

    # compressors back on
    boris.write_register(address=1, value=COMPRESSOR_ON)
    sylvia.write_register(address=1, value=COMPRESSOR_ON)
    sleep(10)

# output_valve_control.off()

while True:
    # are the compressors ON ?
    boris_state = (boris.read_input_registers(address=1)).registers[0]
    sylvia_state = (sylvia.read_input_registers(address=1)).registers[0]

    # get oil temperature
    boris_oil_temp = (boris.read_input_registers(address=42)).registers[0]
    sylvia_oil_temp = (sylvia.read_input_registers(address=42)).registers[0]

    # valve status
    is_on_cold_loop = int(output_valve_control.is_lit)

    # --- InfluxDB Logging ---
    if write_api:
        try:
            p_boris_temp = (
                Point("oil_temperature")
                .tag("compressor", "Boris")
                .field("value", boris_oil_temp / 10.0)
            )
            p_sylvia_temp = (
                Point("oil_temperature")
                .tag("compressor", "Sylvia")
                .field("value", sylvia_oil_temp / 10.0)
            )
            p_boris_state = (
                Point("compressor_state")
                .tag("compressor", "Boris")
                .field("value", boris_state)
            )
            p_sylvia_state = (
                Point("compressor_state")
                .tag("compressor", "Sylvia")
                .field("value", sylvia_state)
            )
            p_valve_state = (
                Point("valve_state")
                .tag("script", "compressor-cooling")
                .field("is_on_cold_loop", is_on_cold_loop)
            )
            p_heartbeat = (
                Point("controller")
                .tag("script", "compressor-cooling")
                .field("heartbeat", 1)
            )

            write_api.write(
                bucket=INFLUXDB_BUCKET,
                org=INFLUXDB_ORG,
                record=[
                    p_boris_temp,
                    p_sylvia_temp,
                    p_boris_state,
                    p_sylvia_state,
                    p_valve_state,
                    p_heartbeat,
                ],
            )
        except InfluxDBError as e:
            print(f"InfluxDB write failed: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during InfluxDB write: {e}")

    # only switch to running water if on cold loop
    if is_on_cold_loop:
        # only consider compressor temp if compressor running
        if boris_state == STATE_RUNNING_CODE:
            if boris_oil_temp > OIL_TEMP_THRESHOLD:
                boris.write_register(address=1, value=COMPRESSOR_OFF)
                output_valve_control.off()  # switch to running water
                sleep(10)
                boris.write_register(address=1, value=COMPRESSOR_ON)

        # only consider compressor temp if compressor running
        if sylvia_state == STATE_RUNNING_CODE:
            if sylvia_oil_temp > OIL_TEMP_THRESHOLD:
                sylvia.write_register(address=1, value=COMPRESSOR_OFF)
                output_valve_control.off()
                sleep(10)
                sylvia.write_register(address=1, value=COMPRESSOR_ON)

    sleep(1)

# output_valve_control.off()
