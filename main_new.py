# This file is part of Astarte.
#
# Copyright 2025 samuele Vecchi
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: MIT 

""" Astarte device example using the MQTT protocol

Example showing how to send/receive individual/aggregated datastreams and set/unset properties.
This version loads only device-owned interfaces to avoid authorization issues.

"""

import asyncio
import time
import tomllib
import json
from pathlib import Path
from threading import Thread
from typing import Optional, Tuple
from datetime import datetime, timezone

from transmit_data import (
    set_properties,
    stream_aggregates,
    stream_individuals,
    unset_properties,
)

from astarte.device import DeviceMqtt
from coffee_machine_simulator import CoffeeMachineSimulator
from getCurrentCounters import getCurrentCounters
from getCurrentSettings import getCurrentSettings
from getCurrentRecipes import getCurrentRecipes
from getCurrentDoses import getCurrentDoses

# Import web server (Flask may not be installed, so handle gracefully)
try:
    from web_server import start_web_server, set_coffee_references
    WEB_SERVER_AVAILABLE = True
except ImportError:
    print("Flask not installed. Web interface will not be available.")
    print("To enable web interface, install Flask: pip install flask")
    WEB_SERVER_AVAILABLE = False

_INTERFACES_DIR = Path(__file__).parent.joinpath("interfaces").absolute()
_CONFIGURATION_FILE = Path(__file__).parent.joinpath("config.toml").absolute()

# Global simulator status object
simulator_status = {
    "counters": {
        "data": {
            "group1": {
                "k1": {"reception_timestamp": "", "timestamp": "", "value": 0},
                "k2": {"reception_timestamp": "", "timestamp": "", "value": 0},
                "k3": {"reception_timestamp": "", "timestamp": "", "value": 0},
                "k4": {"reception_timestamp": "", "timestamp": "", "value": 0},
                "k5": {"reception_timestamp": "", "timestamp": "", "value": 0},
                "k6": {"reception_timestamp": "", "timestamp": "", "value": 0},
                "k7": {"reception_timestamp": "", "timestamp": "", "value": 0},
                "totalCoffee": {"reception_timestamp": "", "timestamp": "", "value": 0}
            },
            "group2": {
                "k1": {"reception_timestamp": "", "timestamp": "", "value": 0},
                "k2": {"reception_timestamp": "", "timestamp": "", "value": 0},
                "k3": {"reception_timestamp": "", "timestamp": "", "value": 0},
                "k4": {"reception_timestamp": "", "timestamp": "", "value": 0},
                "k5": {"reception_timestamp": "", "timestamp": "", "value": 0},
                "k6": {"reception_timestamp": "", "timestamp": "", "value": 0},
                "k7": {"reception_timestamp": "", "timestamp": "", "value": 0},
                "totalCoffee": {"reception_timestamp": "", "timestamp": "", "value": 0}
            },
            "group3": {
                "k1": {"reception_timestamp": "", "timestamp": "", "value": 0},
                "k2": {"reception_timestamp": "", "timestamp": "", "value": 0},
                "k3": {"reception_timestamp": "", "timestamp": "", "value": 0},
                "k4": {"reception_timestamp": "", "timestamp": "", "value": 0},
                "k5": {"reception_timestamp": "", "timestamp": "", "value": 0},
                "k6": {"reception_timestamp": "", "timestamp": "", "value": 0},
                "k7": {"reception_timestamp": "", "timestamp": "", "value": 0},
                "totalCoffee": {"reception_timestamp": "", "timestamp": "", "value": 0}
            },
            "total": {
                "totalCoffee": {"reception_timestamp": "", "timestamp": "", "value": 0},
                "totalVolume": {"reception_timestamp": "", "timestamp": "", "value": 0}
            }
        }
    },
    "settings": {
        "data": {}
    },
    "recipes": {
        "group1": {
            "targetTime": {
                "1": 230,  # 23s 
                "2": 230,  # 23s 
                "3": 270,  # 27s 
                "4": 300   # 30s 
            },
            "dose": {
                "1": 26,  # 26ml
                "2": 37,  # 37ml
                "3": 32,  # 32ml
                "4": 44   # 44ml
            }
        },
        "group2": {
            "targetTime": {
                "1": 230,  # 23s 
                "2": 230,  # 23s 
                "3": 270,  # 27s 
                "4": 300   # 30s 
            },
            "dose": {
                "1": 26,  # 26ml
                "2": 37,  # 37ml
                "3": 32,  # 32ml
                "4": 44   # 44ml
            }
        },
        "group3": {
            "targetTime": {
                "1": 230,  # 23s 
                "2": 230,  # 23s 
                "3": 270,  # 27s 
                "4": 300   # 30s 
            },
            "dose": {
                "1": 26,  # 26ml
                "2": 37,  # 37ml
                "3": 32,  # 32ml
                "4": 44   # 44ml
            }
        }
    },
    "doses": {
        "data": {
            "group1": {
                "k1": {"value": 26, "timestamp": "", "reception_timestamp": ""},  # 26ml
                "k2": {"value": 37, "timestamp": "", "reception_timestamp": ""},  # 37ml
                "k3": {"value": 32, "timestamp": "", "reception_timestamp": ""},  # 32ml
                "k4": {"value": 44, "timestamp": "", "reception_timestamp": ""}   # 44ml
            },
            "group2": {
                "k1": {"value": 26, "timestamp": "", "reception_timestamp": ""},  # 26ml
                "k2": {"value": 37, "timestamp": "", "reception_timestamp": ""},  # 37ml
                "k3": {"value": 32, "timestamp": "", "reception_timestamp": ""},  # 32ml
                "k4": {"value": 44, "timestamp": "", "reception_timestamp": ""}   # 44ml
            },
            "group3": {
                "k1": {"value": 26, "timestamp": "", "reception_timestamp": ""},  # 26ml
                "k2": {"value": 37, "timestamp": "", "reception_timestamp": ""},  # 37ml
                "k3": {"value": 32, "timestamp": "", "reception_timestamp": ""},  # 32ml
                "k4": {"value": 44, "timestamp": "", "reception_timestamp": ""}   # 44ml
            }
        }
    }
}


def on_connected_cbk(_):
    """
    Callback for a connection event.
    """
    print("Device connected.")


def on_data_received_cbk(device, interface_name: str, path: str, payload):
    """
    Callback for a data reception event.
    """
    print(f"Received message for interface: {interface_name} and path: {path}.")
    print(f"    Payload: {payload}")
    
    # If message is from server Settings03 interface, echo it back to device Settings03 interface
    if interface_name == "it.d8pro.server.Settings03":
        try:
            # Update the machine status object with the new setting
            _update_machine_status_setting(path, payload)
            
            print(f"Echoing back to it.d8pro.device.Settings03{path} with payload: {payload}")
            device.send(
                "it.d8pro.device.Settings03",
                path,
                payload
            )
            print(f"Successfully echoed message to device interface")
        except Exception as e:
            print(f"Error echoing message: {e}")
    
    # If message is from server Doses02 interface, echo it back to device Doses02 interface
    elif interface_name == "it.d8pro.server.Doses02":
        try:
            from zoneinfo import ZoneInfo
            current_time = datetime.now(ZoneInfo("Europe/Rome"))
            
            # Update the machine status object with the new dose
            _update_machine_status_dose(path, payload)
            
            print(f"Echoing back to it.d8pro.device.Doses02{path} with payload: {payload}")
            device.send(
                "it.d8pro.device.Doses02",
                path,
                payload,
                timestamp=current_time
            )
            print(f"Successfully echoed dose message to device interface")
        except Exception as e:
            print(f"Error echoing dose message: {e}")


def on_disconnected_cbk(_, reason: int):
    """
    Callback for a disconnection event.
    """
    print("Device disconnected" + (f" because: {reason}." if reason else "."))


def _start_background_loop(_loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(_loop)
    _loop.run_forever()


def _generate_async_loop() -> Tuple[asyncio.AbstractEventLoop, Thread]:
    _loop = asyncio.new_event_loop()
    other_thread = Thread(target=_start_background_loop, args=(_loop,), daemon=True)
    other_thread.start()
    return _loop, other_thread


def is_device_owned_interface(interface_file: Path) -> bool:
    """
    Check if an interface is device-owned by reading its JSON content.
    """
    try:
        with open(interface_file, 'r') as f:
            interface_data = json.load(f)
            ownership = interface_data.get('ownership', '').lower()
            return ownership == 'device'
    except Exception:
        return False


def _update_machine_status_setting(path: str, payload):
    """
    Update the machine status object with a new setting value.
    
    Args:
        path: The setting path (e.g., "/temperature/tempSetpointBoiler")
        payload: The new setting value
    """
    try:
        from zoneinfo import ZoneInfo
        current_time = datetime.now(ZoneInfo("Europe/Rome"))
        
        # Parse the path to extract category and setting name
        # Path format: /category/settingName or /category/subcategory/settingName
        path_parts = path.strip('/').split('/')
        
        if len(path_parts) >= 2:
            category = path_parts[0]
            setting_name = path_parts[1]
            
            # Initialize category if it doesn't exist
            if 'data' not in simulator_status['settings']:
                simulator_status['settings']['data'] = {}
            
            if category not in simulator_status['settings']['data']:
                simulator_status['settings']['data'][category] = {}
            
            # Update the setting value
            simulator_status['settings']['data'][category][setting_name] = payload
            
            print(f"Updated machine status: {category}/{setting_name} = {payload}")
            
        else:
            print(f"Invalid setting path format: {path}")
            
    except Exception as e:
        print(f"Error updating machine status setting: {e}")


def _update_machine_status_dose(path: str, payload):
    """
    Update the machine status object with a new dose value.
    
    Args:
        path: The dose path (e.g., "/group1/k1")
        payload: The new dose value
    """
    try:
        from zoneinfo import ZoneInfo
        current_time = datetime.now(ZoneInfo("Europe/Rome"))
        
        # Parse the path to extract group and dose name
        # Path format: /group/dose (e.g., /group1/k1, /tea/t1)
        path_parts = path.strip('/').split('/')
        
        if len(path_parts) >= 2:
            group = path_parts[0]
            dose_name = path_parts[1]
            
            # Initialize doses data structure if it doesn't exist
            if 'data' not in simulator_status['doses']:
                simulator_status['doses']['data'] = {}
            
            if group not in simulator_status['doses']['data']:
                simulator_status['doses']['data'][group] = {}
            
            # Update the dose value
            simulator_status['doses']['data'][group][dose_name] = payload
            
            print(f"Updated machine dose: {group}/{dose_name} = {payload}")
            
        else:
            print(f"Invalid dose path format: {path}")
            
    except Exception as e:
        print(f"Error updating machine status dose: {e}")


def _send_status_updates(device: DeviceMqtt):
    """
    Send machine and group status updates after connection.
    """
    try:
        from zoneinfo import ZoneInfo
        current_time = datetime.now(ZoneInfo("Europe/Rome"))
        
        # Send machine status
        print("Sending machine status...")
        device.send(
            "it.d8pro.device.TelemetryFast01",
            "/machineStatus",
            1,
            timestamp=current_time
        )
        print("Machine status sent: 1")
        
        # Small delay between sends
        time.sleep(0.1)
        
        # Send group statuses
        group_statuses = ["gr1Status", "gr2Status", "gr3Status"]
        for group_status in group_statuses:
            print(f"Sending {group_status}...")
            device.send(
                "it.d8pro.device.TelemetrySlow01",
                f"/{group_status}",
                1,
                timestamp=current_time
            )
            print(f"{group_status} sent: 1")
            time.sleep(0.1)  # Small delay between sends
            
        print("All status updates sent successfully")
        
    except Exception as e:
        print(f"Error sending status updates: {e}")


def main(cb_loop: Optional[asyncio.AbstractEventLoop] = None):

    with open(_CONFIGURATION_FILE, "rb") as config_fp:
        config = tomllib.load(config_fp)
        _DEVICE_ID = config["DEVICE_ID"]
        _REALM = config["REALM"]
        _CREDENTIALS_SECRET = config["CREDENTIALS_SECRET"]
        _PAIRING_URL = config["PAIRING_URL"]
        _STREAM_INDIVIDUAL_DATA = config.get("STREAM_INDIVIDUAL_DATA", True)
        _STREAM_AGGREGATED_DATA = config.get("STREAM_AGGREGATED_DATA", True)
        _SET_PROPERTIES = config.get("SET_PROPERTIES", True)
        _UNSET_PROPERTIES = config.get("UNSET_PROPERTIES", True)
        _WAIT_FOR_INCOMING_S = config.get("WAIT_FOR_INCOMING_S", 0)

    # Use a persistent directory to avoid file locking issues
    import os
    persist_dir = os.path.join(os.getcwd(), "astarte_persistence")
    if not os.path.exists(persist_dir):
        os.makedirs(persist_dir)

    print("Creating and connecting the device.")
    
    # Instantiate the device
    device = DeviceMqtt(
        device_id=_DEVICE_ID,
        realm=_REALM,
        credentials_secret=_CREDENTIALS_SECRET,
        pairing_base_url=_PAIRING_URL,
        persistency_dir=persist_dir,
        ignore_ssl_errors=True
    )
    
    # Load device-owned interfaces and the server Settings03 interface for message listening
    interface_files = list(_INTERFACES_DIR.glob("*.json"))
    interfaces_to_load = []
    
    for interface_file in interface_files:
        # Load device-owned interfaces
        if is_device_owned_interface(interface_file):
            interfaces_to_load.append(interface_file)
        # Also load server interfaces to receive incoming messages
        elif interface_file.name in ["it.d8pro.server.Settings03.json", "it.d8pro.server.Doses02.json"]:
            interfaces_to_load.append(interface_file)
    
    for interface_file in interfaces_to_load:
        try:
            device.add_interface_from_file(interface_file)
            print(f"Loaded interface: {interface_file.name}")
        except Exception as e:
            print(f"Failed to load {interface_file.name}: {e}")
    
    # Set all the callback functions
    device.set_events_callbacks(
        on_connected=on_connected_cbk,
        on_data_received=on_data_received_cbk,
        on_disconnected=on_disconnected_cbk,
        loop=cb_loop,
    )
    
    # Connect the device
    device.connect()
    
    # Wait for connection
    connection_timeout = 30
    start_time = time.time()
    
    while not device.is_connected():
        elapsed_time = time.time() - start_time
        if elapsed_time > connection_timeout:
            print(f"Connection timeout after {connection_timeout} seconds")
            return
            
        print("connecting")
        time.sleep(1)

    time.sleep(1)
    
    # Send machine and group status updates
    print("Sending machine and group status updates...")
    _send_status_updates(device)
    
    # Get current counters from the API
    print("Getting current counters...")
    current_counters = getCurrentCounters()
    #print("Current counters retrieved:", current_counters)
    
    # Update simulator_status with retrieved counters
    if current_counters and 'data' in current_counters:
        simulator_status["counters"] = current_counters
        print("Simulator status updated with current counters")
    else:
        print("Using default counter values")
    
    # Get current settings from the API
    print("Getting current settings...")
    current_settings = getCurrentSettings()
    #print("Current settings retrieved:", current_settings)
    
    # Update simulator_status with retrieved settings
    if current_settings and 'data' in current_settings:
        simulator_status["settings"] = current_settings
        print("Simulator status updated with current settings")
    else:
        print("Using default settings values")
    """
    # Get current recipes from the API
    print("Getting current recipes...")
    current_recipes = getCurrentRecipes()
    #print("Current recipes retrieved:", current_recipes)
    
    # Update simulator_status with retrieved recipes
    if current_recipes:
        simulator_status["recipes"] = current_recipes
        print("Simulator status updated with current recipes")
    else:
        print("Using default recipes values")
    """
    # Get current doses from the API
    print("Getting current doses...")
    current_doses = getCurrentDoses()
    #print("Current doses retrieved:", current_doses)
    
    # Update simulator_status with retrieved doses
    if current_doses and 'data' in current_doses:
        simulator_status["doses"] = current_doses
        print("Simulator status updated with current doses")
    else:
        print("Using default doses values")
    
    # Initialize and start the coffee machine simulator
    coffee_simulator = CoffeeMachineSimulator(device, simulator_status)
    coffee_simulator.start_simulation()
    
    # Start web server if Flask is available
    if WEB_SERVER_AVAILABLE:
        set_coffee_references(device, coffee_simulator, simulator_status)
        web_thread = start_web_server()
        print("Web interface available at: http://localhost:5000")
    else:
        print("Web interface not available (Flask not installed)")
    
    # Keep the simulation running
    print("Coffee machine simulation is running. Press Ctrl+C to stop.")
    try:
        while device.is_connected():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down coffee machine simulation...")
        coffee_simulator.stop_simulation()
        

        
# If called as a script
if __name__ == "__main__":

    # [Optional] Preparing a different asyncio loop for the callbacks to prevent deadlocks
    # Replace with loop = None to run the Astarte event callback in the main thread
    print("Generating async loop.")
    (loop, thread) = _generate_async_loop()
    main(loop)
    loop.call_soon_threadsafe(loop.stop)
    print("Requested async loop stop.")
    thread.join()
    print("Async loop stopped.")
