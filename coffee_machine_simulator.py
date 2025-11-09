"""
Coffee Machine Simulator for Astarte Device

This module simulates a coffee machine with 3 groups that can brew coffee
at random intervals and send telemetry data to the Astarte platform.
"""

import random
import time
import threading
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, Dict, Any
from astarte.device import DeviceMqtt


class CoffeeMachineSimulator:
    """
    Simulates a coffee machine with 3 groups that brew coffee at random intervals.
    """
    
    def __init__(self, device: DeviceMqtt, simulator_status: Optional[Dict[str, Any]] = None, interface_name: str = "it.d8pro.device.TelemetryFast01", save_status_callback=None):
        self.device = device
        self.interface_name = interface_name
        self.simulator_status = simulator_status or {}
        self.save_status_callback = save_status_callback  # Callback to save simulator status
        self.groups = ["group1", "group2", "group3"]
        self.coffee_types = [1, 2, 3, 4, 5, 6, 7]  # 7 different coffee types
        self.running = False
        self.threads = []
        self.group_status = {group: "idle" for group in self.groups} # Track status of each group: idle, brewing, washing
        # Load active alarms from simulator_status if available
        self.active_alarms: Dict[str, bool] = self.simulator_status.get('alarms', {}) # Store active alarms, e.g., {"/critical/general": True, "/major/group3HeatingTimeout": True}
        
        # Manual washing tracking
        self.last_washing_date = None
        self.washing_in_progress = False
        self.daily_washing_completed = False

        # Define alarm types for easier management
        self.critical_alarms = {
            "/critical/generalLoadingTimeout",
            "/critical/boilerNtcOpen",
            "/critical/boilerNtcShort",
            "/critical/boilerHeatingTimeout"
        }
        self.group_blocking_major_alarms = {
            "group1": [
                "/major/group1HeatingTimeout",
                "/major/group1HmiCommError",
                "/major/group1NtcOpen",
                "/major/group1NtcShort"
            ],
            "group2": [
                "/major/group2HeatingTimeout",
                "/major/group2HmiCommError",
                "/major/group2NtcOpen",
                "/major/group2NtcShort"
            ],
            "group3": [
                "/major/group3HeatingTimeout",
                "/major/group3HmiCommError",
                "/major/group3NtcOpen",
                "/major/group3NtcShort"
            ]
        }
        self.non_blocking_major_alarms = {
            "/major/cupNtcOpen",
            "/major/cupNtcShort",
            "/major/cupHeatingTimeout"
        }
        
        # Initialize total litres tracking (in tens of ml to match flowTotal units)
        self.total_litres_tens_ml = 0
        self.initial_filter_duration = self._get_water_filter_duration_setting()
        
        # Initialize temperature tracking
        self.last_temp_update = {}  # Track last temperature update time for each group
        self.current_temps = {}     # Track current temperatures for each group
        
        # Initialize scheduler settings
        self.scheduler_data = self.simulator_status.get('scheduler', {})
        self.default_scheduler_values = {
            "/calendarEnabled": False,
            "/ev1Time": 0, "/ev1Data": 0,
            "/ev2Time": 0, "/ev2Data": 0,
            "/ev3Time": 0, "/ev3Data": 0,
            "/ev4Time": 0, "/ev4Data": 0,
            "/ev5Time": 0, "/ev5Data": 0,
            "/ev6Time": 0, "/ev6Data": 0,
            "/ev7Time": 0, "/ev7Data": 0,
            "/ev8Time": 0, "/ev8Data": 0,
            "/ev9Time": 0, "/ev9Data": 0,
            "/ev10Time": 0, "/ev10Data": 0
        }
        
    def set_alarm(self, alarm_path: str, payload):
        """Set or unset an alarm. Handles both boolean and integer payloads."""
        # Convert payload to boolean for internal storage
        # For boolean payloads: True/False
        # For integer payloads: 0 = False, non-zero = True
        if isinstance(payload, bool):
            active = payload
        elif isinstance(payload, int):
            active = payload != 0
        else:
            # Try to convert to boolean
            active = bool(payload)
        
        print(f"Setting alarm '{alarm_path}' to {active} (original payload: {payload})")
        self.active_alarms[alarm_path] = active
        
        # Also update the simulator_status to persist the alarm state
        if self.simulator_status is not None:
            if 'alarms' not in self.simulator_status:
                self.simulator_status['alarms'] = {}
            self.simulator_status['alarms'][alarm_path] = active
            print(f"Updated simulator_status alarms: {alarm_path} = {active}")
        
    def start_simulation(self):
        """Start the coffee machine simulation."""
        if self.running:
            print("Coffee machine simulation is already running.")
            return
            
        self.running = True
        print("Starting coffee machine simulation...")
        
        # Send initial flow error for each group
        self._send_initial_flow_errors()
        
        # Start a thread for each group
        for group in self.groups:
            thread = threading.Thread(target=self._simulate_group, args=(group,), daemon=True)
            thread.start()
            self.threads.append(thread)
        
    def stop_simulation(self):
        """Stop the coffee machine simulation."""
        self.running = False
        print("Stopping coffee machine simulation...")
        
    def _simulate_group(self, group: str):
        """Simulate coffee brewing for a specific group with realistic coffee shop schedule."""
        while self.running:
            if not self.device.is_connected():
                time.sleep(1)
                continue
            
            # Check if coffee shop is open (7:00 AM to 11:00 PM)
            current_time = datetime.now(ZoneInfo("Europe/Rome"))
            current_hour = current_time.hour
            
            # Coffee shop is closed from 11 PM to 7 AM
            if current_hour >= 23 or current_hour < 7:
                print(f"Coffee shop closed at {current_time.strftime('%H:%M')} - {group} sleeping")
                time.sleep(60)  # Check every minute during closed hours
                continue
            
            # Check if this is the first group and shop is just opening (7:00-7:30 AM)
            # Perform daily manual washing before starting coffee operations
            if group == "group1" and current_hour == 7 and not self.daily_washing_completed:
                self._check_and_perform_daily_washing(current_time)
            
            # Wait if washing is in progress
            if self.washing_in_progress:
                print(f"{group} waiting - manual washing in progress")
                time.sleep(30)  # Check every 30 seconds during washing
                continue
            
            # Calculate wait time based on hour of day for realistic coffee shop patterns
            wait_time = self._get_realistic_wait_time(current_hour)
            
            # Sleep in small intervals to allow for quick shutdown
            for _ in range(wait_time):
                if not self.running:
                    return
                time.sleep(1)
                
            if not self.running:
                return
                
            # Check again if shop is still open after waiting
            current_time = datetime.now(ZoneInfo("Europe/Rome"))
            current_hour = current_time.hour
            if current_hour >= 23 or current_hour < 7:
                continue
                
            # Simulate brewing coffee
            self._brew_coffee(group)
            
    def _brew_coffee(self, group: str, coffee_type: Optional[int] = None):
        """Simulate brewing coffee on a specific group."""
        print(f"Brew coffee from simulator")
        if not self.device.is_connected():
            return
            
        # --- Alarm Checks ---
        # --- Alarm Checks ---
        # 1. Critical Alarms: Prevents all brewing
        for alarm_path in self.critical_alarms:
            if self.active_alarms.get(alarm_path, False):
                print(f"Cannot brew on {group}: Critical alarm '{alarm_path}' is active.")
                self.group_status[group] = "idle"
                return

        # 2. Major Alarms: Affect specific groups, except for certain exceptions.
        is_blocking_major_alarm_active = False
        
        # Check for active major alarms
        for alarm_path, is_active in self.active_alarms.items():
            if is_active and alarm_path.startswith("/major/"):
                # Skip non-blocking major alarms
                if alarm_path in self.non_blocking_major_alarms:
                    continue
                
                # Check if this is a blocking major alarm for the current group
                if group in self.group_blocking_major_alarms:
                    if alarm_path in self.group_blocking_major_alarms[group]:
                        print(f"Cannot brew on {group}: Blocking major alarm '{alarm_path}' is active.")
                        is_blocking_major_alarm_active = True
                        break # Found a blocking alarm for this group
        
        if is_blocking_major_alarm_active:
            self.group_status[group] = "idle"
            return
        # --- End Alarm Checks ---

        # Check if the group is already brewing
        if self.group_status.get(group) == "brewing":
            print(f"Skipping brew for {group}: already brewing.")
            return
            
        try:
            # Set group status to brewing
            self.group_status[group] = "brewing"
            source = "manual"
            # Generate coffee data - use provided coffee_type or random selection
            if coffee_type is None:
                coffee_type = random.choice(self.coffee_types)
                source = "simulator"
                
                
            # a purge every 3  coffees
            purgeChance = random.randint(0, 100)
            print(purgeChance)
            if purgeChance > 60:
                print(f"purge {self.interface_name} /{group}/coffeeType")
                current_time = datetime.now(ZoneInfo("Europe/Rome"))
                
                self.device.send(
                    self.interface_name,
                    f"/{group}/coffeeType",
                    8,
                    timestamp=current_time
                )
                
                time.sleep(4)
                current_time = datetime.now(ZoneInfo("Europe/Rome"))
                self._update_and_send_counters(group, 8, 350, current_time)
                self._add_brewing_log(group, 8, int(40/10), int(350/10), current_time, source)
            else:
                print("no purge")
            
            
            erog_time = self._get_erog_time_for_coffee_type(group, coffee_type)
            flow_total = self._get_flow_total_for_coffee_type(group, coffee_type)
            
            print(f"Brewing coffee on {group}: type={coffee_type}, erogTime={erog_time}, flowTotal={flow_total}")
            
            volume = 0 # volume in ml
            #print(f"flow={volume}, volume: {flow_total}")
           
            flowRate = flow_total/erog_time # 2 ml/sec
            print(f"computed flow rate: {flowRate} ml/sec")
            step = 0.2
            timer=0
            while (volume <= flow_total/10):
                volume = volume + flowRate*0.2
                delta = random.randint(-1, 1)
                flowRate = flowRate + delta/10
                flowRate = max(min(5, flowRate), .5)
                progress = 1000*volume/flow_total
                print(f"\rflowRate: {flowRate:.1f} ml/s, brewed volume: {volume:.1f}, progress: {progress:.1f}%", end='', flush=True)
                timer=timer + step
                time.sleep(step)
            
                self.device.send(
                    "it.d8pro.device.TelemetryFast01",
                    f"/{group}/flowRate",
                    int(10*flowRate),
                    timestamp=datetime.now(ZoneInfo("Europe/Rome"))
                )
            
            #print(f"\nflowRate: {flowRate:.1f} ml/s, brewed volume: {volume:.1f}")
            #print(f"timer: {10*timer}")
            
            self.device.send(
                    "it.d8pro.device.TelemetryFast01",
                    f"/{group}/flowRate",
                    0,
                    timestamp=datetime.now(ZoneInfo("Europe/Rome"))
            )
            
            current_time = datetime.now(ZoneInfo("Europe/Rome"))
            
            
            # Send coffee type
            self.device.send(
                self.interface_name,
                f"/{group}/coffeeType",
                coffee_type,
                timestamp=current_time
            )
            #print(f"sent coffee_type: {coffee_type}")
            # Small delay between sends
            time.sleep(0.1)
            
            # Send erogation time
            self.device.send(
                self.interface_name,
                f"/{group}/erogTime",
                int(10*timer),
                timestamp=current_time
            )
            #print(f"sent erogTime: {int(10*timer)}")
            # Small delay between sends
            time.sleep(0.1)
            
            # Send flow total
            self.device.send(
                self.interface_name,
                f"/{group}/flowTotal",
                flow_total,
                timestamp=current_time
            )
            #print(f"sent flow_total: {flow_total}")
            # Update counters and send to Counters02 interface
            self._update_and_send_counters(group, coffee_type, flow_total, current_time)
            
            # Check if we need to update temperature for this group
            self._check_and_update_temperature(group, current_time)
            
            # Add log entry for this brewing event
            
            self._add_brewing_log(group, coffee_type, int(erog_time/10), int(flow_total/10), current_time, source)

            # Reset group status to idle after brewing is complete
            self.group_status[group] = "idle"
            
        except Exception as e:
            print(f"Error brewing coffee on {group}: {e}")
            # Ensure status is reset even if an error occurs during brewing
            self.group_status[group] = "idle"
            
    def _send_initial_flow_errors(self):
        """Send initial flow error for each group at startup."""
        if not self.device.is_connected():
            return
            
        current_time = datetime.now(ZoneInfo("Europe/Rome"))
        
        for group in self.groups:
            try:
                print(f"Sending initial flow error for {group}")
                self.device.send(
                    self.interface_name,
                    f"/{group}/flowError",
                    False,
                    timestamp=current_time
                )
                time.sleep(0.1)  # Small delay between sends
                
            except Exception as e:
                print(f"Error sending initial flow error for {group}: {e}")
    
    def _update_and_send_counters(self, group: str, coffee_type: int, flow_total: int, current_time: datetime):
        """Update simulator counters and send to Counters02 interface."""
        if not self.simulator_status or 'counters' not in self.simulator_status:
            print("No simulator status available for counter updates")
            return
            
        try:
            counters_data = self.simulator_status['counters']['data']
            
            # Determine coffee count increment based on coffee type
            # Add 1 for coffee type 1 and 2, add 2 for coffee type 3 and 4
            if coffee_type in [1, 2]:
                coffee_increment = 1
            elif coffee_type in [3, 4]:
                coffee_increment = 2
            elif coffee_type == 8:  # Purge
                coffee_increment = 1
            else:
                coffee_increment = 1  # Default for types 5, 6, 7
            
            # Update group-specific coffee type counter (k1-k7)
            if coffee_type < 8:
                coffee_key = f"k{coffee_type}"
            elif coffee_type == 8:
                coffee_key = f"purge"
            
            # Ensure the group exists in counters_data
            if group not in counters_data:
                counters_data[group] = {}
            
            # Initialize the coffee key if it doesn't exist
            if coffee_key not in counters_data[group]:
                counters_data[group][coffee_key] = {
                    'value': 0,
                    'timestamp': current_time.isoformat(),
                    'reception_timestamp': current_time.isoformat()
                }
                print(f"Initialized missing counter {group}/{coffee_key}")
            
            # Update the counter
            counters_data[group][coffee_key]['value'] += coffee_increment
            counters_data[group][coffee_key]['timestamp'] = current_time.isoformat()
            counters_data[group][coffee_key]['reception_timestamp'] = current_time.isoformat()
            
            # Send updated counter to Astarte
            self.device.send(
                "it.d8pro.device.Counters02",
                f"/{group}/{coffee_key}",
                counters_data[group][coffee_key]['value'],
                timestamp=current_time
            )
            print(f"Updated {group}/{coffee_key}: {counters_data[group][coffee_key]['value']}")
            
            # Update group total coffee counter (exclude purges as they are cleaning operations)
            if coffee_type != 8:  # Don't count purges in total coffee
                # Initialize totalCoffee if it doesn't exist
                if 'totalCoffee' not in counters_data[group]:
                    counters_data[group]['totalCoffee'] = {
                        'value': 0,
                        'timestamp': current_time.isoformat(),
                        'reception_timestamp': current_time.isoformat()
                    }
                    print(f"Initialized missing counter {group}/totalCoffee")
                
                counters_data[group]['totalCoffee']['value'] += coffee_increment
                counters_data[group]['totalCoffee']['timestamp'] = current_time.isoformat()
                counters_data[group]['totalCoffee']['reception_timestamp'] = current_time.isoformat()
                
                # Send updated group total to Astarte
                self.device.send(
                    "it.d8pro.device.Counters02",
                    f"/{group}/totalCoffee",
                    counters_data[group]['totalCoffee']['value'],
                    timestamp=current_time
                )
                print(f"Updated {group}/totalCoffee: {counters_data[group]['totalCoffee']['value']}")
                
                # Update total coffee counter
                if 'totalCoffee' in counters_data['total']:
                    counters_data['total']['totalCoffee']['value'] += coffee_increment
                    counters_data['total']['totalCoffee']['timestamp'] = current_time.isoformat()
                    counters_data['total']['totalCoffee']['reception_timestamp'] = current_time.isoformat()
                    
                    # Send updated total coffee to Astarte
                    self.device.send(
                        "it.d8pro.device.Counters02",
                        "/total/totalCoffee",
                        counters_data['total']['totalCoffee']['value'],
                        timestamp=current_time
                    )
                    print(f"Updated total/totalCoffee: {counters_data['total']['totalCoffee']['value']}")
            else:
                print(f"Purge operation - not counting in totalCoffee counters")
            
            # Update total volume (flow_total/10)
            volume_increment = flow_total / 10
            if 'totalVolume' in counters_data['total']:
                counters_data['total']['totalVolume']['value'] += volume_increment
                counters_data['total']['totalVolume']['timestamp'] = current_time.isoformat()
                counters_data['total']['totalVolume']['reception_timestamp'] = current_time.isoformat()
                
                # Send updated total volume to Astarte
                self.device.send(
                    "it.d8pro.device.Counters02",
                    "/total/totalVolume",
                    counters_data['total']['totalVolume']['value'],
                    timestamp=current_time
                )
                print(f"Updated total/totalVolume: {counters_data['total']['totalVolume']['value']}")
            
            # Update residualCoffeeActivation (decrease by 1 for each coffee, but not for purges)
            if coffee_type != 8:  # Don't affect maintenance counter for purges
                self._update_residual_coffee_activation(current_time)
            
            # Update maintenance counters
            self._update_maintenance_counters(flow_total, current_time)

            # Save simulator status to file after updating counters
            if self.save_status_callback:
                if self.save_status_callback(self.simulator_status):
                    print(f"✓ Simulator status saved to file after {group}/{coffee_key} update")
                else:
                    print(f"✗ Failed to save simulator status after {group}/{coffee_key} update")

        except Exception as e:
            print(f"Error updating counters: {e}")
    
    def _update_residual_coffee_activation(self, current_time: datetime):
        """Update residualCoffeeActivation counter (decrease by 1 for each coffee)."""
        try:
            # Initialize residualCoffeeActivation if it doesn't exist in counters
            counters_data = self.simulator_status['counters']['data']
            
            if 'total' not in counters_data:
                counters_data['total'] = {}
            
            if 'residualCoffeeActivation' not in counters_data['total']:
                # Get initial value from settings if available
                initial_value = self._get_residual_coffee_setting()
                counters_data['total']['residualCoffeeActivation'] = {
                    'value': initial_value,
                    'timestamp': current_time.isoformat(),
                    'reception_timestamp': current_time.isoformat()
                }
                print(f"Initialized residualCoffeeActivation: {initial_value}")
            
            # Decrease by 1 for each coffee brewed
            current_value = counters_data['total']['residualCoffeeActivation']['value']
            new_value = current_value - 1
            
            # Update the counter
            counters_data['total']['residualCoffeeActivation']['value'] = new_value
            counters_data['total']['residualCoffeeActivation']['timestamp'] = current_time.isoformat()
            counters_data['total']['residualCoffeeActivation']['reception_timestamp'] = current_time.isoformat()
            
            # Send updated counter to Astarte
            self.device.send(
                "it.d8pro.device.Counters02",
                "/residualCoffeeActivation",
                new_value,
                timestamp=current_time
            )
            print(f"Updated residualCoffeeActivation: {current_value} -> {new_value}")
            
        except Exception as e:
            print(f"Error updating residualCoffeeActivation: {e}")
    
    def _get_residual_coffee_setting(self) -> int:
        """Get the residualCoffeeForManteinance setting value or default."""
        try:
            if (self.simulator_status and 
                'settings' in self.simulator_status and 
                'data' in self.simulator_status['settings'] and
                'manteinance' in self.simulator_status['settings']['data'] and
                'residualCoffeeForManteinance' in self.simulator_status['settings']['data']['manteinance']):
                
                value = self.simulator_status['settings']['data']['manteinance']['residualCoffeeForManteinance']
                print(f"Using residualCoffeeForManteinance from settings: {value}")
                return value
            else:
                print("Using default residualCoffeeActivation value: 10000")
                return 10000  # Default value
                
        except Exception as e:
            print(f"Error getting residual coffee setting: {e}")
            return 10000  # Default fallback
    
    def _get_water_filter_duration_setting(self) -> int:
        """Get the waterFilterDuration setting value or default."""
        try:
            if (self.simulator_status and 
                'settings' in self.simulator_status and 
                'data' in self.simulator_status['settings'] and
                'manteinance' in self.simulator_status['settings']['data'] and
                'waterFilterDuration' in self.simulator_status['settings']['data']['manteinance']):
                
                value = self.simulator_status['settings']['data']['manteinance']['waterFilterDuration']
                print(f"Using waterFilterDuration from settings: {value}")
                return value
            else:
                print("Using default waterFilterDuration value: 5000")
                return 5000  # Default value
                
        except Exception as e:
            print(f"Error getting water filter duration setting: {e}")
            return 5000  # Default fallback
    
    def _update_maintenance_counters(self, flow_total: int, current_time: datetime):
        """Update maintenance-related counters."""
        try:
            # Update total litres tracking (flow_total is in tens of ml)
            self.total_litres_tens_ml += flow_total
            
            # Get current residualCoffeeActivation value for residualPumpActivation
            maintenance_data = self.simulator_status['maintenance']['data']
            residual_coffee_value = 0
            
            if ('manteinance' in maintenance_data and 
                'residualPumpActivation' in maintenance_data['manteinance']):
                residual_coffee_value = maintenance_data['manteinance']['residualPumpActivation']['value']
            
            residual_coffee_value =  residual_coffee_value -1
            
            # Send residualPumpActivation (same as residualCoffeeActivation)
            self.device.send(
                "it.d8pro.device.TelemetrySlow01",
                "/manteinance/residualPumpActivation",
                residual_coffee_value,
                timestamp=current_time
            )
            print(f"Updated manteinance/residualPumpActivation: {residual_coffee_value}")
            
            # Calculate residualFilterLiters (initial filter duration - total litres used)
            # Convert tens of ml to litres: divide by 100 (10 tens of ml = 1 ml, 1000 ml = 1 litre)
            total_litres = self.total_litres_tens_ml / 100.0  # Convert to litres
            residual_filter_litres = self.initial_filter_duration - total_litres
            
            # Convert to integer as required by the interface
            residual_filter_litres_int = int(residual_filter_litres)
            
            # Send residualFilterLiters
            self.device.send(
                "it.d8pro.device.TelemetrySlow01",
                "/manteinance/residualFilterLiters",
                residual_filter_litres_int,
                timestamp=current_time
            )
            print(f"Updated manteinance/residualFilterLiters: {residual_filter_litres_int} (total used: {total_litres:.2f}L)")
            
        except Exception as e:
            print(f"Error updating maintenance counters: {e}")
    
    def _get_realistic_wait_time(self, current_hour: int) -> int:
        """
        Calculate realistic wait time between coffees based on coffee shop hours.
        
        Target: 350-450 coffees per day distributed across 3 groups (16 hours open)
        Peak hours: 7-10 AM and 12-2 PM (high volume)
        Regular hours: 10 AM-12 PM, 2-6 PM, 6-11 PM (lower volume)
        
        Args:
            current_hour: Current hour (0-23)
            
        Returns:
            int: Wait time in seconds before next coffee
        """
        # Total target coffees per day: 400 (middle of 350-450 range)
        # Distributed across 3 groups = ~133 coffees per group per day
        # Open 16 hours (7 AM to 11 PM)
        
        if 7 <= current_hour < 10:
            # Morning rush: 7-10 AM (3 hours) - 40% of daily volume
            # ~53 coffees per group in 3 hours = ~18 coffees/hour = 1 coffee every 3.3 minutes
            base_wait = 200  # 3.3 minutes = 200 seconds
            variation = 60   # ±1 minute variation
            
        elif 12 <= current_hour < 14:
            # Lunch rush: 12-2 PM (2 hours) - 25% of daily volume  
            # ~33 coffees per group in 2 hours = ~16.5 coffees/hour = 1 coffee every 3.6 minutes
            base_wait = 220  # 3.6 minutes = 220 seconds
            variation = 60   # ±1 minute variation
            
        elif 10 <= current_hour < 12:
            # Mid-morning: 10 AM-12 PM (2 hours) - 15% of daily volume
            # ~20 coffees per group in 2 hours = ~10 coffees/hour = 1 coffee every 6 minutes
            base_wait = 360  # 6 minutes = 360 seconds
            variation = 120  # ±2 minutes variation
            
        elif 14 <= current_hour < 18:
            # Afternoon: 2-6 PM (4 hours) - 15% of daily volume
            # ~20 coffees per group in 4 hours = ~5 coffees/hour = 1 coffee every 12 minutes
            base_wait = 720  # 12 minutes = 720 seconds
            variation = 180  # ±3 minutes variation
            
        else:
            # Evening: 6-11 PM (5 hours) - 5% of daily volume
            # ~7 coffees per group in 5 hours = ~1.4 coffees/hour = 1 coffee every 43 minutes
            base_wait = 2580  # 43 minutes = 2580 seconds
            variation = 600   # ±10 minutes variation
        
        # Add random variation
        min_wait = max(30, base_wait - variation)  # Minimum 30 seconds
        max_wait = base_wait + variation
        
        wait_time = random.randint(min_wait, max_wait)
        
        # Log the wait time for debugging
        hour_description = self._get_hour_description(current_hour)
        print(f"Coffee shop hour {current_hour}:00 ({hour_description}) - Next coffee in {wait_time//60}m {wait_time%60}s")
        
        return wait_time
    
    def _get_hour_description(self, hour: int) -> str:
        """Get a description of the current hour period."""
        if 7 <= hour < 10:
            return "Morning Rush"
        elif 12 <= hour < 14:
            return "Lunch Rush"
        elif 10 <= hour < 12:
            return "Mid-Morning"
        elif 14 <= hour < 18:
            return "Afternoon"
        elif 18 <= hour < 23:
            return "Evening"
        else:
            return "Closed"

    def _check_and_update_temperature(self, group: str, current_time: datetime):
        """
        Check if temperature needs to be updated for a group and update it if necessary.
        Temperature is updated every 10-20 minutes and varies around the setpoint.
        
        Args:
            group: Group name (group1, group2, group3)
            current_time: Current datetime
        """
        try:
            # Check if enough time has passed since last temperature update
            if group not in self.last_temp_update:
                # First time - initialize and send temperature
                self._update_group_temperature(group, current_time)
                return
            
            # Calculate time since last update
            time_diff = (current_time - self.last_temp_update[group]).total_seconds()
            
            # Update every 10-20 minutes (600-1200 seconds)
            update_interval = random.randint(600, 1200)
            
            if time_diff >= update_interval:
                self._update_group_temperature(group, current_time)
                
        except Exception as e:
            print(f"Error checking temperature update for {group}: {e}")
    
    def _update_group_temperature(self, group: str, current_time: datetime):
        """
        Update the current temperature for a specific group.
        
        Args:
            group: Group name (group1, group2, group3)
            current_time: Current datetime
        """
        try:
            # Get temperature setpoint for this group
            setpoint = self._get_temperature_setpoint(group)
            
            # Generate realistic temperature variation around setpoint (±2-5°C)
            variation = random.uniform(-2.0, 2.0)
            current_temp = setpoint + variation
            
            # Round to 1 decimal place
            current_temp = round(current_temp, 1)
            
            # Convert to tenths of degrees for transmission (93.0°C becomes 930)
            temp_tenths = int(current_temp * 10)
            
            # Store current temperature and update time
            self.current_temps[group] = current_temp
            self.last_temp_update[group] = current_time
            
            # Send temperature to TelemetryFast01 interface (in tenths of degrees)
            self.device.send(
                self.interface_name,
                f"/{group}/currentTemp",
                temp_tenths,
                timestamp=current_time
            )
            
            print(f"Updated {group} temperature: {current_temp}°C (sent: {temp_tenths} tenths) (setpoint: {setpoint}°C)")
            
        except Exception as e:
            print(f"Error updating temperature for {group}: {e}")
    
    def _get_temperature_setpoint(self, group: str) -> float:
        """
        Get the temperature setpoint for a specific group from TelemetrySlow01 interface.
        
        Args:
            group: Group name (group1, group2, group3)
            
        Returns:
            float: Temperature setpoint in Celsius
        """
        try:
            # Map group names to setpoint paths
            group_mapping = {
                "group1": "gr1TempSetpoint",
                "group2": "gr2TempSetpoint", 
                "group3": "gr3TempSetpoint"
            }
            
            setpoint_path = group_mapping.get(group)
            if not setpoint_path:
                print(f"Unknown group: {group}, using default setpoint")
                return 90.0  # Default setpoint
            
            # Try to get setpoint from simulator status or settings
            # For now, use realistic default values for coffee machine groups
            default_setpoints = {
                "group1": 92.0,  # Typical espresso temperature
                "group2": 90.0,
                "group3": 92.5
            }
            
            if (self.simulator_status and 
                    'maintenance' in self.simulator_status ):
                default_setpoints['group1'] = self.simulator_status['maintenance']['data']['gr1TempSetpoint']['value']/10
                default_setpoints['group2'] = self.simulator_status['maintenance']['data']['gr2TempSetpoint']['value']/10
                default_setpoints['group3'] = self.simulator_status['maintenance']['data']['gr3TempSetpoint']['value']/10
            
            setpoint = default_setpoints.get(group, 90.0)
            
            
            return setpoint
            
        except Exception as e:
            print(f"Error getting temperature setpoint for {group}: {e}")
            return 90.0  # Fallback default

    def _get_erog_time_for_coffee_type(self, group: str, coffee_type: int) -> int:
        """Get erogation time for a coffee type based on recipe or default random."""
        try:
            # For coffee types 1-4, try to get target time from recipes
            if coffee_type in [1, 2, 3, 4]:
                if (self.simulator_status and 
                    'recipes' in self.simulator_status and 
                    group in self.simulator_status['recipes']):
                    
                    recipe_data = self.simulator_status['recipes'][group]
                    
                    # Check if recipe has targetTime for this coffee type
                    if ('targetTime' in recipe_data and 
                        str(coffee_type) in recipe_data['targetTime']):
                        
                        target_time = recipe_data['targetTime'][str(coffee_type)]
                        
                        # Generate random time around target (±15%)
                        variation = int(target_time * 0.15)
                        min_time = target_time - variation
                        max_time = target_time + variation
                        
                        # Ensure minimum time is at least 50s
                        min_time = max(min_time, 50)
                        
                        erog_time = random.randint(min_time, max_time)
                        delta = 100*abs(erog_time-target_time)/target_time
                        print(f"Using recipe target time for {group} K{coffee_type}: {target_time}ms (generated: {erog_time}ms delta= {delta:.1f}%) ")
                        return erog_time
            
            # Default random time for types 5-7 or when no recipe available
            default_time = random.randint(150, 350)
            print(f"Using default random time for {group} K{coffee_type}: {default_time}ms")
            return default_time
            
        except Exception as e:
            print(f"Error getting erog time for {group} K{coffee_type}: {e}")
            return random.randint(150, 350)  # Fallback to default

    def _get_flow_total_for_coffee_type(self, group: str, coffee_type: int) -> int:
        """
        Get flow total for a coffee type based on doses or default random.
        
        Args:
            group: Group name (group1, group2, group3)
            coffee_type: Coffee type (1-7)
            
        Returns:
            int: Flow total in tens of ml (dose_ml * 10)
        """
        try:
            # For coffee types 1-4, try to get dose from doses data
            if coffee_type in [1, 2, 3, 4]:
                if (self.simulator_status and 
                    'doses' in self.simulator_status and 
                    'data' in self.simulator_status['doses'] and
                    group in self.simulator_status['doses']['data']):
                    
                    doses_data = self.simulator_status['doses']['data'][group]
                    dose_key = f"k{coffee_type}"
                    
                    # Check if dose exists for this coffee type
                    if dose_key in doses_data:
                        if isinstance(doses_data[dose_key], dict) and 'value' in doses_data[dose_key]:
                            dose_ml = doses_data[dose_key]['value']
                        else:
                            # Handle case where dose_key contains direct value
                            dose_ml = doses_data[dose_key]
                        
                        # Convert dose from tens of ml to flow_total format (ml)
                        flow_total = int(dose_ml)
                        print(f"Using dose for {group} K{coffee_type}: {dose_ml}ml (flow_total: {flow_total})")
                        return flow_total
                    else:
                        print(f"Dose key {dose_key} not found for {group}, using random value")
                else:
                    print(f"Doses data not available for {group}, using random value")
            
            # Default random flow_total for types 5-7 or when no dose available
            # Keep the same range as before (300-600 = 30-60ml)
            flow_total = random.randint(300, 600)
            print(f"Using random flow_total for {group} K{coffee_type}: {flow_total} (volume: {flow_total/10}ml)")
            return flow_total
            
        except Exception as e:
            print(f"Error getting flow_total for {group} K{coffee_type}: {e}")
            # Fallback to random value
            return random.randint(300, 600)

    def _add_brewing_log(self, group: str, coffee_type: int, duration: int, volume: int, timestamp: datetime, source: str):
        """
        Add a brewing event to the log in simulator_status.
        
        Args:
            group: Group name (group1, group2, group3)
            coffee_type: Coffee type (1-7)
            duration: Brewing duration in milliseconds (erog_time)
            volume: Flow volume (flow_total)
            timestamp: Brewing timestamp
            source: Source of the brewing event ("simulator" or "manual")
        """
        try:
            if not self.simulator_status:
                print("No simulator status available for brewing log")
                return
            
            # Initialize brewing_logs if it doesn't exist
            if 'brewing_logs' not in self.simulator_status:
                self.simulator_status['brewing_logs'] = []
            
            # Create log entry
            log_entry = {
                'timestamp': timestamp.isoformat(),
                'group': group,
                'coffee_type': coffee_type,
                'duration': duration,
                'volume': volume,
                'source': source
            }
            
            # Add to logs
            self.simulator_status['brewing_logs'].append(log_entry)
            
            # Keep only the last 1000 entries to prevent the file from growing too large
            max_logs = 1000
            if len(self.simulator_status['brewing_logs']) > max_logs:
                self.simulator_status['brewing_logs'] = self.simulator_status['brewing_logs'][-max_logs:]
            
            print(f"Added brewing log: {group} K{coffee_type} - {duration}ms, {volume}ml ({source})")
            
        except Exception as e:
            print(f"Error adding brewing log: {e}")

    def _check_and_perform_daily_washing(self, current_time: datetime):
        """
        Check if daily washing needs to be performed and execute it.
        
        Args:
            current_time: Current datetime
        """
        try:
            current_date = current_time.date()
            
            # Check if washing has already been performed today
            if (self.last_washing_date is not None and 
                self.last_washing_date == current_date):
                self.daily_washing_completed = True
                return
            
            # Check if it's the right time for washing (7:00-7:30 AM)
            if current_time.hour == 7 and current_time.minute <= 30:
                print(f"🧼 Starting daily manual washing at {current_time.strftime('%H:%M:%S')}")
                self._manual_washing(current_time)
                
                # Update washing status
                self.last_washing_date = current_date
                self.daily_washing_completed = True
                
                self.device.send(
                    self.interface_name,
                    f"/group1/coffeeType",
                    9,
                    timestamp=current_time
                )
                
                self.device.send(
                    self.interface_name,
                    f"/group2/coffeeType",
                    9,
                    timestamp=current_time
                )
                                
                self.device.send(
                    self.interface_name,
                    f"/group3/coffeeType",
                    9,
                    timestamp=current_time
                )
                
                time.sleep(40)
                
                print(f"✅ Daily manual washing completed at {current_time.strftime('%H:%M:%S')}")
                
        except Exception as e:
            print(f"Error during daily washing check: {e}")
            self.washing_in_progress = False

    def _manual_washing(self, current_time: datetime):
        """
        Daily manual washing routine called automatically at shop opening.
        
        This function will be called every morning at shop opening (7:00-7:30 AM) 
        to perform the daily manual washing routine.
        
        Args:
            current_time: Current datetime when washing starts
        """
        try:
            # Set washing in progress to prevent brewing during washing
            self.washing_in_progress = True
            
            # Call the simulator manual washing function
            self._simulator_manual_washing(current_time)
            
        except Exception as e:
            print(f"Error during daily manual washing: {e}")
        finally:
            # Always reset washing status
            self.washing_in_progress = False

    def _simulator_manual_washing(self, current_time: datetime):
        """
        Simulator function for manual washing implementation.
        
        This is the main function where you should implement the washing simulation logic.
        It will be called both for daily automatic washing and manual washing operations.
        
        Args:
            current_time: Current datetime when washing starts
            
        TODO: Implement the actual washing simulation logic here.
        This function should:
        1. Simulate the washing process for all groups
        2. Send appropriate telemetry data during washing
        3. Log the washing operation
        4. Handle any washing-related counters or maintenance data
        """
        print(f"🧼 Starting manual washing simulation at {current_time.strftime('%H:%M:%S')}")
        
        # TODO: Add your washing simulation logic here
        # Examples of what you might implement:
        # - Send washing flow rates to telemetry
        # - Update washing counters
        # - Simulate washing duration with realistic timing
        # - Send washing status indicators
        # - Update maintenance data
        
        # Placeholder implementation - replace with your washing logic
        print("🔄 Washing simulation placeholder - implement your washing logic here")
        
        # Example: You might want to simulate washing flow rates
        # for group in self.groups:
        #     # Simulate washing flow rate
        #     self.device.send(
        #         self.interface_name,
        #         f"/{group}/flowRate",
        #         washing_flow_rate,
        #         timestamp=current_time
        #     )
        
        print("✅ Manual washing simulation completed")

    def _start_manual_washing(self, group: str):
        """
        Placeholder for starting manual washing on a specific group.
        
        This function will be called from the web interface when the manual 
        washing button is pressed for a specific group.
        
        Args:
            group: Group name (group1, group2, group3)
        """
        print(f"Starting manual washing for {group}")
        # TODO: Implement manual washing logic for specific group here
        pass

    def _start_automatic_washing(self, group: str):
        """
        Placeholder for starting automatic washing on a specific group.
        
        This function will be called from the web interface when the automatic 
        washing button is pressed for a specific group.
        
        Args:
            group: Group name (group1, group2, group3)
        """
        print(f"Starting automatic washing for {group}")
        # TODO: Implement automatic washing logic for specific group here
        pass

    def _start_purge(self, group: str):
        """
        Placeholder for starting purge operation on a specific group.
        
        This function will be called from the web interface when the purge 
        button is pressed for a specific group.
        
        Args:
            group: Group name (group1, group2, group3)
        """
        print(f"Starting purge for {group}")
        # TODO: Implement purge logic for specific group here
        pass

    def load_scheduler_settings_from_cloud(self):
        """Load scheduler settings from cloud, using defaults if none exist."""
        try:
            from getCurrentScheduler import main as get_scheduler_data
            cloud_data = get_scheduler_data()
            
            # Merge with defaults to ensure all fields exist
            scheduler_data = self.default_scheduler_values.copy()
            if cloud_data:
                scheduler_data.update(cloud_data)
            
            self.scheduler_data = scheduler_data
            
            # Persist to simulator status
            if self.simulator_status is not None:
                self.simulator_status['scheduler'] = scheduler_data
                
            print("Scheduler settings loaded successfully")
            return scheduler_data
            
        except Exception as e:
            print(f"Error loading scheduler settings from cloud: {e}")
            print("Using default scheduler settings")
            self.scheduler_data = self.default_scheduler_values.copy()
            if self.simulator_status is not None:
                self.simulator_status['scheduler'] = self.scheduler_data
            return self.scheduler_data

    def send_scheduler_data_to_cloud(self):
        """Send current scheduler data to cloud via device interface."""
        try:
            device_interface = "it.d8pro.device.Scheduler01"
            
            for endpoint, value in self.scheduler_data.items():
                try:
                    self.device.send(device_interface, endpoint, value)
                    print(f"Sent scheduler property {endpoint}: {value}")
                except Exception as e:
                    print(f"Error sending scheduler property {endpoint}: {e}")
                    
        except Exception as e:
            print(f"Error sending scheduler data to cloud: {e}")

    def handle_scheduler_data_from_server(self, interface: str, path: str, payload):
        """Handle scheduler data received from server and echo it back via device interface."""
        try:
            if interface == "it.d8pro.server.Scheduler01":
                print(f"Received scheduler data from server: {path} = {payload}")
                
                # Update local scheduler data
                if path in self.scheduler_data:
                    self.scheduler_data[path] = payload
                    
                    # Persist to simulator status
                    if self.simulator_status is not None:
                        if 'scheduler' not in self.simulator_status:
                            self.simulator_status['scheduler'] = {}
                        self.simulator_status['scheduler'][path] = payload
                    
                    # Echo back to device interface
                    try:
                        device_interface = "it.d8pro.device.Scheduler01"
                        self.device.send(device_interface, path, payload)
                        print(f"Echoed scheduler data back to device interface: {path} = {payload}")
                    except Exception as e:
                        print(f"Error echoing scheduler data back: {e}")
                else:
                    print(f"Unknown scheduler endpoint received: {path}")
                    
        except Exception as e:
            print(f"Error handling scheduler data from server: {e}")