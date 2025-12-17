from time import sleep
from gpiozero import Button, LED, PWMOutputDevice
from pymodbus.client import ModbusTcpClient
import numpy as np
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.exceptions import InfluxDBError
from dotenv import load_dotenv
import os
import time

load_dotenv()

STATE_RUNNING_CODE = 3  # 3 means running
MAX_DISCONNECT_TIME = 5 * 60  # 5 minutes in seconds

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

OIL_TEMP_THRESHOLD = 300  # x10 Celcius
COMPRESSOR_ON = 0x001
COMPRESSOR_OFF = 0x00FF

def create_boris_compressor_connection():
    """Create and connect a Modbus TCP client."""
    boris = ModbusTcpClient("192.168.1.2", port=502)
    if not boris.connect():
        print("Failed to connect to Boris compressor Modbus server.")
        return None
    return boris

def create_sylvia_compressor_connection():
    """Create and connect a Modbus TCP client."""
    sylvia = ModbusTcpClient("192.168.0.2", port=502)
    if not sylvia.connect():
        print("Failed to connect to Sylvia compressor Modbus server.")
        return None
    return sylvia

def poll_compressor_state(client):
    try:
        result = client.read_input_registers(address=1)
        if result and not result.isError():
            return result.registers[0]
        else:
            print("Read error or invalid response for compressor state.")
            return None
    except Exception as e:
        print(f"Exception during Modbus read of compressor state: {e}")
        return None

def poll_oil_temperature(client):
    try:
        result = client.read_input_registers(address=42)
        if result and not result.isError():
            return result.registers[0]
        else:
            print("Read error or invalid response for compressor state.")
            return None
    except Exception as e:
        print(f"Exception during Modbus read of compressor state: {e}")
        return None

go_to_cold_loop = True
#output_valve_control.on()

# create connections
boris = create_boris_compressor_connection()
sylvia = create_sylvia_compressor_connection()

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

# initiate times of last good connection
boris_last_reading_compressor_state_success_time = time.time()
sylvia_last_reading_compressor_state_success_time = time.time()
boris_last_reading_temperature_oil_success_time = time.time()
sylvia_last_reading_temperature_oil_success_time = time.time()

# output_valve_control.off()

while True:
    # === valve status ===
    is_on_cold_loop = int(output_valve_control.is_lit)

    # === Switch if disconnected for too long ===
    boris_disconnected_duration = max(time.time() - boris_last_reading_compressor_state_success_time,
                                      time.time() - boris_last_reading_temperature_oil_success_time,)
    sylvia_disconnected_duration = max(time.time() - sylvia_last_reading_compressor_state_success_time,
                                        time.time() - sylvia_last_reading_temperature_oil_success_time,)
    # if only one fridge is not well connected, OK
    disconnected_duration = min(boris_disconnected_duration, sylvia_disconnected_duration)
    if (disconnected_duration >= MAX_DISCONNECT_TIME) and is_on_cold_loop:
        # we don't turn off compressor
        output_valve_control.off()  # switch to running water
        sleep(10)


    # === check connections are fine, recreate if not ===
    if boris is None:
        # Try reconnecting
        boris = create_boris_compressor_connection()
        if boris is None:
            sleep(5)  # wait before retry
            continue # return to the while
    if sylvia is None:
        # Try reconnecting
        sylvia = create_sylvia_compressor_connection()
        if sylvia is None:
            sleep(5)  # wait before retry
            continue # return to the while

    # === compressor state ===
    boris_state = poll_compressor_state(boris)
    if boris_state is None:
        # Connection may have dropped; reconnect
        boris.close()
        boris = None
        sleep(1)  # wait before retry
        continue  # return to the while
    else:
        # everything's fine -> reset success time
        boris_last_reading_compressor_state_success_time = time.time()

    sylvia_state = poll_compressor_state(sylvia)
    if sylvia_state is None:
        # Connection may have dropped; reconnect
        sylvia.close()
        sylvia = None
        sleep(1)  # wait before retry
        continue  # return to the while
    else:
        # everything's fine -> reset success time
        sylvia_last_reading_compressor_state_success_time = time.time()


    # === oil temperature ===
    boris_oil_temp = poll_oil_temperature(boris)
    if boris_oil_temp is None:
        # Connection may have dropped; reconnect
        boris.close()
        boris = None
        sleep(1)  # wait before retry
        continue  # return to the while
    else:
        # everything's fine -> reset success time
        boris_last_reading_temperature_oil_success_time = time.time()

    sylvia_oil_temp = poll_oil_temperature(sylvia)
    if sylvia_oil_temp is None:
        # Connection may have dropped; reconnect
        sylvia.close()
        sylvia = None
        sleep(1)  # wait before retry
        continue  # return to the while
    else:
        # everything's fine -> reset success time
        sylvia_last_reading_temperature_oil_success_time = time.time()

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
            if boris_oil_temp >= OIL_TEMP_THRESHOLD:
                boris.write_register(address=1, value=COMPRESSOR_OFF)
                output_valve_control.off()  # switch to running water
                sleep(10)
                boris.write_register(address=1, value=COMPRESSOR_ON)

        # only consider compressor temp if compressor running
        if sylvia_state == STATE_RUNNING_CODE:
            if sylvia_oil_temp >= OIL_TEMP_THRESHOLD:
                sylvia.write_register(address=1, value=COMPRESSOR_OFF)
                output_valve_control.off()
                sleep(10)
                sylvia.write_register(address=1, value=COMPRESSOR_ON)

    sleep(1)

# output_valve_control.off()
