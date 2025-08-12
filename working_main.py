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

""" Astarte device example using the MQTT protocol - WORKING VERSION

This version addresses the MQTT disconnect reason code 7 (NOT_AUTHORIZED) issue
by only loading device-owned interfaces initially to avoid authorization problems.

"""

import asyncio
import tempfile
import time
import tomllib
import logging
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

_INTERFACES_DIR = Path(__file__).parent.joinpath("interfaces").absolute()
_CONFIGURATION_FILE = Path(__file__).parent.joinpath("config.toml").absolute()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def on_connected_cbk(device):
    """
    Callback for a connection event.
    """
    print("✅ Device connected successfully!")
    logger.info("Device connected successfully!")


def on_data_received_cbk(device, interface_name: str, path: str, payload):
    """
    Callback for a data reception event.
    """
    print(f"📨 Received message for interface: {interface_name} and path: {path}.")
    print(f"    Payload: {payload}")
    logger.info(f"Received message for interface: {interface_name} and path: {path}. Payload: {payload}")


def on_disconnected_cbk(device, reason: int):
    """
    Callback for a disconnection event.
    """
    if reason == 0:
        print("✅ Device disconnected gracefully.")
        logger.info("Device disconnected gracefully.")
    else:
        print(f"❌ Device disconnected with reason: {reason}")
        logger.warning(f"Device disconnected with reason: {reason}")


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
    except Exception as e:
        logger.error(f"Error reading interface {interface_file}: {e}")
        return False


def main(cb_loop: Optional[asyncio.AbstractEventLoop] = None):
    try:
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

        print("🔧 Configuration loaded:")
        print(f"   Device ID: {_DEVICE_ID}")
        print(f"   Realm: {_REALM}")
        print(f"   Pairing URL: {_PAIRING_URL}")
        
        logger.info(f"Configuration loaded - Device ID: {_DEVICE_ID}, Realm: {_REALM}")

        # Use a persistent directory to avoid file locking issues
        import os
        persist_dir = os.path.join(os.getcwd(), "astarte_persistence")
        if not os.path.exists(persist_dir):
            os.makedirs(persist_dir)
            
        print(f"📁 Using persistence directory: {persist_dir}")
        logger.info(f"Using persistence directory: {persist_dir}")

        print("🔌 Creating device...")
        logger.info("Creating device")
        
        # Instantiate the device
        device = DeviceMqtt(
            device_id=_DEVICE_ID,
            realm=_REALM,
            credentials_secret=_CREDENTIALS_SECRET,
            pairing_base_url=_PAIRING_URL,
            persistency_dir=persist_dir,
            ignore_ssl_errors=True  # Enable for debugging
        )
        
        # Load only device-owned interfaces to avoid authorization issues
        print("📋 Loading device-owned interfaces only...")
        logger.info("Loading device-owned interfaces only")
        
        interface_files = list(_INTERFACES_DIR.glob("*.json"))
        device_interfaces = []
        server_interfaces = []
        
        for interface_file in interface_files:
            if is_device_owned_interface(interface_file):
                device_interfaces.append(interface_file)
            else:
                server_interfaces.append(interface_file)
        
        print(f"Found {len(device_interfaces)} device-owned interfaces:")
        for interface_file in device_interfaces:
            try:
                print(f"   Loading: {interface_file.name}")
                device.add_interface_from_file(interface_file)
                logger.info(f"Successfully loaded device interface: {interface_file.name}")
            except Exception as e:
                print(f"   ❌ Failed to load {interface_file.name}: {e}")
                logger.error(f"Failed to load interface {interface_file.name}: {e}")
        
        print(f"Skipping {len(server_interfaces)} server-owned interfaces to avoid authorization issues:")
        for interface_file in server_interfaces:
            print(f"   Skipped: {interface_file.name}")
        
        # Set callbacks
        print("🔗 Setting up callbacks...")
        logger.info("Setting up callbacks")
        device.set_events_callbacks(
            on_connected=on_connected_cbk,
            on_data_received=on_data_received_cbk,
            on_disconnected=on_disconnected_cbk,
            loop=cb_loop,
        )
        
        # Connect the device
        print("🚀 Attempting to connect...")
        logger.info("Attempting to connect")
        device.connect()
        
        # Wait for connection
        connection_timeout = 30
        start_time = time.time()
        
        while not device.is_connected():
            elapsed_time = time.time() - start_time
            if elapsed_time > connection_timeout:
                print(f"❌ Connection timeout after {connection_timeout} seconds")
                logger.error(f"Connection timeout after {connection_timeout} seconds")
                return
                
            print(f"⏳ Connecting... ({elapsed_time:.1f}s)")
            time.sleep(1)

        print("✅ Device connected and staying connected!")
        logger.info("Device connected and staying connected!")
        
        # Now that we're connected, let's run the data transmission functions
        if device.is_connected():
            print("📊 Starting data transmission...")
            
            device.send(
                    "it.d8pro.device.TelemetryFast01",
                    "/group2/flowError",
                    False,
                    datetime.now(tz=timezone.utc),)
            i=0
            while(True):
                time.sleep(1)
                i=i+1
                device.send(
                    "it.d8pro.device.TelemetryFast01",
                    "/group2/flowError",
                    False,
                    datetime.now(tz=timezone.utc),)
                if i % 10 == 0 and i > 0:
                    print(f"   Still waiting... ({i}/{_WAIT_FOR_INCOMING_S}s)")
            
            

        
        print("✅ Script completed successfully!")

    except Exception as e:
        print(f"❌ Error occurred: {e}")
        logger.error(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()


# If called as a script
if __name__ == "__main__":
    try:
        print("🔄 Starting Astarte device connection...")
        
        # Use async loop as in original
        print("🔄 Generating async loop...")
        (loop, thread) = _generate_async_loop()
        main(loop)
        loop.call_soon_threadsafe(loop.stop)
        print("🛑 Requested async loop stop...")
        thread.join()
        print("✅ Async loop stopped.")
        
    except KeyboardInterrupt:
        print("\n🛑 Script interrupted by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
