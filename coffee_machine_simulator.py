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
    
    def __init__(self, device: DeviceMqtt, simulator_status: Optional[Dict[str, Any]] = None, interface_name: str = "it.d8pro.device.TelemetryFast01"):
        self.device = device
        self.interface_name = interface_name
        self.simulator_status = simulator_status or {}
        self.groups = ["group1", "group2", "group3"]
        self.coffee_types = [1, 2, 3, 4, 5, 6, 7]  # 7 different coffee types
        self.running = False
        self.threads = []
        
        # Initialize total litres tracking (in tens of ml to match flowTotal units)
        self.total_litres_tens_ml = 0
        self.initial_filter_duration = self._get_water_filter_duration_setting()
        
        # Initialize temperature tracking
        self.last_temp_update = {}  # Track last temperature update time for each group
        self.current_temps = {}     # Track current temperatures for each group
        
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
            
    def _brew_coffee(self, group: str):
        """Simulate brewing coffee on a specific group."""
        if not self.device.is_connected():
            return
            
        try:
            # Generate random coffee data
            coffee_type = random.choice(self.coffee_types)
            erog_time = self._get_erog_time_for_coffee_type(group, coffee_type)
            flow_total = random.randint(300, 600)
            
            current_time = datetime.now(ZoneInfo("Europe/Rome"))
            
            print(f"Brewing coffee on {group}: type={coffee_type}, erogTime={erog_time}, flowTotal={flow_total}")
            
            # Send coffee type
            self.device.send(
                self.interface_name,
                f"/{group}/coffeeType",
                coffee_type,
                timestamp=current_time
            )
            
            # Small delay between sends
            time.sleep(0.1)
            
            # Send erogation time
            self.device.send(
                self.interface_name,
                f"/{group}/erogTime",
                erog_time,
                timestamp=current_time
            )
            
            # Small delay between sends
            time.sleep(0.1)
            
            # Send flow total
            self.device.send(
                self.interface_name,
                f"/{group}/flowTotal",
                flow_total,
                timestamp=current_time
            )
            
            # Update counters and send to Counters02 interface
            self._update_and_send_counters(group, coffee_type, flow_total, current_time)
            
            # Check if we need to update temperature for this group
            self._check_and_update_temperature(group, current_time)
            
        except Exception as e:
            print(f"Error brewing coffee on {group}: {e}")
            
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
            else:
                coffee_increment = 1  # Default for types 5, 6, 7
            
            # Update group-specific coffee type counter (k1-k7)
            coffee_key = f"k{coffee_type}"
            
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
            
            # Update group total coffee counter
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
            
            # Update residualCoffeeActivation (decrease by 1 for each coffee)
            self._update_residual_coffee_activation(current_time)
            
            # Update maintenance counters
            self._update_maintenance_counters(flow_total, current_time)
                
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
            counters_data = self.simulator_status['counters']['data']
            residual_coffee_value = 0
            
            if ('total' in counters_data and 
                'residualCoffeeActivation' in counters_data['total']):
                residual_coffee_value = counters_data['total']['residualCoffeeActivation']['value']
            
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
            variation = random.uniform(-5.0, 5.0)
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
            
            setpoint = default_setpoints.get(group, 90.0)
            
            # TODO: In the future, this could read from actual TelemetrySlow01 data
            # if available in simulator_status
            
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
                        
                        # Generate random time around target (±35%)
                        variation = int(target_time * 0.15)
                        min_time = target_time - variation
                        max_time = target_time + variation
                        
                        # Ensure minimum time is at least 50s
                        min_time = max(min_time, 50)
                        
                        erog_time = random.randint(min_time, max_time)
                        print(f"Using recipe target time for {group} K{coffee_type}: {target_time}ms (generated: {erog_time}ms)")
                        return erog_time
            
            # Default random time for types 5-7 or when no recipe available
            default_time = random.randint(150, 350)
            print(f"Using default random time for {group} K{coffee_type}: {default_time}ms")
            return default_time
            
        except Exception as e:
            print(f"Error getting erog time for {group} K{coffee_type}: {e}")
            return random.randint(150, 350)  # Fallback to default
