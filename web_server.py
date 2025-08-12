"""
Flask Web Server for Coffee Machine Simulator Control

This module provides a web interface to control the coffee machine simulator,
allowing users to update settings and manually trigger coffee brewing.
"""

from flask import Flask, request, jsonify, send_from_directory, render_template_string
import threading
import time
import random
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any
import json

# Import data retrieval functions
from getCurrentCounters import getCurrentCounters
from getCurrentSettings import getCurrentSettings
from getCurrentDoses import getCurrentDoses
from getCurrentRecipes import getCurrentRecipes

# Global variables to store the device and simulator references
coffee_device = None
coffee_simulator = None
simulator_status = None

app = Flask(__name__)

@app.route('/')
def index():
    """Serve the main HTML page."""
    return send_from_directory('.', 'coffee_control_web.html')

@app.route('/settings')
def settings_page():
    """Display settings configuration page."""
    try:
        # Get current settings from LOCAL simulator
        current_settings = get_local_settings()
        
        # Get connection status
        connection_status = "Connected" if (coffee_device and coffee_device.is_connected()) else "Disconnected"
        
        # Get current timestamp
        current_time = datetime.now(ZoneInfo("Europe/Rome")).strftime("%Y-%m-%d %H:%M:%S %Z")
        
        # Prepare data for template
        settings_data = {
            'connection_status': connection_status,
            'current_time': current_time,
            'settings': current_settings or {'data': {}}
        }
        
        return render_template_string(SETTINGS_PAGE_TEMPLATE, **settings_data)
        
    except Exception as e:
        error_message = f"Error loading settings page: {str(e)}"
        return render_template_string(ERROR_TEMPLATE, error=error_message), 500

@app.route('/machine-interface')
def machine_interface_page():
    """Display machine interface page."""
    try:
        # Get connection status
        connection_status = "Connected" if (coffee_device and coffee_device.is_connected()) else "Disconnected"
        
        # Get current timestamp
        current_time = datetime.now(ZoneInfo("Europe/Rome")).strftime("%Y-%m-%d %H:%M:%S %Z")
        
        # Prepare data for template
        interface_data = {
            'connection_status': connection_status,
            'current_time': current_time
        }
        
        return render_template_string(MACHINE_INTERFACE_TEMPLATE, **interface_data)
        
    except Exception as e:
        error_message = f"Error loading machine interface page: {str(e)}"
        return render_template_string(ERROR_TEMPLATE, error=error_message), 500

@app.route('/status')
def status_page():
    """Display comprehensive status page with all coffee machine data from LOCAL simulator."""
    try:
        # Get current data from LOCAL simulator status instead of remote API
        current_counters = get_local_counters()
        current_settings = get_local_settings()
        current_doses = get_local_doses()
        current_recipes = get_local_recipes()
        
        # Get connection status
        connection_status = "Connected" if (coffee_device and coffee_device.is_connected()) else "Disconnected"
        
        # Get current timestamp
        current_time = datetime.now(ZoneInfo("Europe/Rome")).strftime("%Y-%m-%d %H:%M:%S %Z")
        
        # Prepare data for template with safe defaults
        status_data = {
            'connection_status': connection_status,
            'current_time': current_time,
            'counters': current_counters or {'data': {}},
            'settings': current_settings or {'data': {}},
            'doses': current_doses or {'data': {}},
            'recipes': current_recipes or {},
            'simulator_status': simulator_status or {}
        }
        
        return render_template_string(STATUS_PAGE_TEMPLATE, **status_data)
        
    except Exception as e:
        error_message = f"Error loading status page: {str(e)}"
        return render_template_string(ERROR_TEMPLATE, error=error_message), 500

@app.route('/api/get_current_settings', methods=['GET'])
def get_current_settings():
    """Get current settings from the local simulator status."""
    try:
        # Get current settings from LOCAL simulator status
        settings_data = get_local_settings()
        
        if settings_data:
            return jsonify({
                'success': True,
                'settings': settings_data
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No settings data available in local simulator'
            })
            
    except Exception as e:
        print(f"Error in get_current_settings: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/update_settings', methods=['POST'])
def update_settings():
    """Update coffee machine settings."""
    try:
        settings_data = request.json
        
        if not settings_data:
            return jsonify({'error': 'No settings data provided'}), 400
        
        if not coffee_device or not coffee_device.is_connected():
            return jsonify({'error': 'Coffee machine not connected'}), 500
        
        current_time = datetime.now(ZoneInfo("Europe/Rome"))
        updated_count = 0
        
        # Send each setting to the device
        for path, value in settings_data.items():
            try:
                # Try sending without timestamp first (for properties interfaces)
                try:
                    coffee_device.send(
                        "it.d8pro.device.Settings03",
                        path,
                        value
                    )
                except Exception as timestamp_error:
                    # If that fails, try with timestamp (for datastream interfaces)
                    if "timestamp" in str(timestamp_error).lower():
                        coffee_device.send(
                            "it.d8pro.device.Settings03",
                            path,
                            value,
                            timestamp=current_time
                        )
                    else:
                        raise timestamp_error
                
                updated_count += 1
                print(f"Updated setting {path} = {value}")
                
                # Small delay between sends
                time.sleep(0.05)
                
            except Exception as e:
                print(f"Error updating setting {path}: {e}")
        
        return jsonify({
            'success': True,
            'message': f'Updated {updated_count} settings successfully'
        })
        
    except Exception as e:
        print(f"Error in update_settings: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/update_doses', methods=['POST'])
def update_doses():
    """Update coffee machine doses."""
    try:
        doses_data = request.json
        
        if not doses_data:
            return jsonify({'error': 'No doses data provided'}), 400
        
        if not coffee_device or not coffee_device.is_connected():
            return jsonify({'error': 'Coffee machine not connected'}), 500
        
        current_time = datetime.now(ZoneInfo("Europe/Rome"))
        updated_count = 0
        
        # Send each dose to the device
        for path, value in doses_data.items():
            try:
                coffee_device.send(
                    "it.d8pro.device.Doses02",
                    path,
                    value,
                    timestamp=current_time
                )
                updated_count += 1
                print(f"Updated dose {path} = {value}")
                
                # Small delay between sends
                time.sleep(0.05)
                
            except Exception as e:
                print(f"Error updating dose {path}: {e}")
        
        return jsonify({
            'success': True,
            'message': f'Updated {updated_count} doses successfully'
        })
        
    except Exception as e:
        print(f"Error in update_doses: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/brew_coffee', methods=['POST'])
def brew_coffee():
    """Manually trigger coffee brewing for a specific type on a specific group."""
    try:
        data = request.json
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        coffee_type = data.get('coffee_type')
        group = data.get('group', 'group1')  # Default to group1 if not specified
        
        if not coffee_type or coffee_type not in range(1, 8):
            return jsonify({'error': 'Invalid coffee type. Must be 1-7'}), 400
        
        if group not in ['group1', 'group2', 'group3']:
            return jsonify({'error': 'Invalid group. Must be group1, group2, or group3'}), 400
        
        if not coffee_device or not coffee_device.is_connected():
            return jsonify({'error': 'Coffee machine not connected'}), 500
        
        # Simulate brewing coffee manually
        brewing_result = manual_brew_coffee(coffee_type, group)
        
        if brewing_result['success']:
            return jsonify({
                'success': True,
                'message': f'Coffee K{coffee_type} brewed successfully on {group}',
                'brewing_info': {
                    'coffee_type': coffee_type,
                    'group': group,
                    'duration': brewing_result['erog_time'],
                    'flow_total': brewing_result['flow_total']
                }
            })
        else:
            return jsonify({'error': 'Failed to brew coffee'}), 500
            
    except Exception as e:
        print(f"Error in brew_coffee: {e}")
        return jsonify({'error': str(e)}), 500

def manual_brew_coffee(coffee_type: int, group: str = "group1") -> Dict[str, Any]:
    """Manually brew a specific coffee type on a specific group."""
    try:
        if not coffee_device or not coffee_device.is_connected():
            return {'success': False, 'error': 'Device not connected'}
        
        # Generate coffee data using recipe-based erogation time
        erog_time = _get_erog_time_for_coffee_type(group, coffee_type)
        flow_total = random.randint(300, 600)
        
        current_time = datetime.now(ZoneInfo("Europe/Rome"))
        
        print(f"Manual brewing coffee: group={group}, type={coffee_type}, erogTime={erog_time}, flowTotal={flow_total}")
        
        
        brewingtime = erog_time
        while (brewingtime >= 0):
            brewingtime = brewingtime - 20
            flowRate = random.randint(10, 60)
            print(f"flowRate: {flowRate}")
            time.sleep(flowRate/100)
        
            coffee_device.send(
                "it.d8pro.device.TelemetryFast01",
                f"/{group}/flowRate",
                flowRate,
                timestamp=current_time
            )
        
        # Send coffee telemetry data
        coffee_device.send(
            "it.d8pro.device.TelemetryFast01",
            f"/{group}/coffeeType",
            coffee_type,
            timestamp=current_time
        )
        
        time.sleep(0.1)
        
        coffee_device.send(
            "it.d8pro.device.TelemetryFast01",
            f"/{group}/erogTime",
            erog_time,
            timestamp=current_time
        )
        
        time.sleep(0.1)
        
        coffee_device.send(
            "it.d8pro.device.TelemetryFast01",
            f"/{group}/flowTotal",
            flow_total,
            timestamp=current_time
        )
        
        # Update counters if simulator is available
        if coffee_simulator and hasattr(coffee_simulator, '_update_and_send_counters'):
            coffee_simulator._update_and_send_counters(group, coffee_type, flow_total, current_time)
        
        return {
            'success': True,
            'erog_time': erog_time,
            'flow_total': flow_total
        }
        
    except Exception as e:
        print(f"Error in manual_brew_coffee: {e}")
        return {'success': False, 'error': str(e)}

def _get_erog_time_for_coffee_type(group: str, coffee_type: int) -> int:
    """Get erogation time for a coffee type based on recipe or default random."""
    try:
        # For coffee types 1-4, try to get target time from recipes
        if coffee_type in [1, 2, 3, 4]:
            if (simulator_status and 
                'recipes' in simulator_status and 
                group in simulator_status['recipes']):
                
                recipe_data = simulator_status['recipes'][group]
                
                # Check if recipe has targetTime for this coffee type
                if ('targetTime' in recipe_data and 
                    str(coffee_type) in recipe_data['targetTime']):
                    
                    target_time = recipe_data['targetTime'][str(coffee_type)]
                    
                    # Generate random time around target (±35%)
                    variation = int(target_time * 0.35)
                    min_time = target_time - variation
                    max_time = target_time + variation
                    
                    # Ensure minimum time is at least 50ms
                    min_time = max(min_time, 50)
                    
                    erog_time = random.randint(min_time, max_time)
                    print(f"Web: Using recipe target time for {group} K{coffee_type}: {target_time}ms (generated: {erog_time}ms)")
                    return erog_time
        
        # Default random time for types 5-7 or when no recipe available
        default_time = random.randint(150, 350)
        print(f"Web: Using default random time for {group} K{coffee_type}: {default_time}ms")
        return default_time
        
    except Exception as e:
        print(f"Web: Error getting erog time for {group} K{coffee_type}: {e}")
        return random.randint(150, 350)  # Fallback to default

def get_local_counters():
    """Get counters data from local simulator status."""
    if simulator_status and 'counters' in simulator_status:
        return simulator_status['counters']
    return None

def get_local_settings():
    """Get settings data from local simulator status."""
    if simulator_status and 'settings' in simulator_status:
        return simulator_status['settings']
    return None

def get_local_doses():
    """Get doses data from local simulator status."""
    if simulator_status and 'doses' in simulator_status:
        return simulator_status['doses']
    return None

def get_local_recipes():
    """Get recipes data from local simulator status."""
    if simulator_status and 'recipes' in simulator_status:
        return simulator_status['recipes']
    return {}

def set_coffee_references(device, simulator, status):
    """Set references to the coffee device and simulator."""
    global coffee_device, coffee_simulator, simulator_status
    coffee_device = device
    coffee_simulator = simulator
    simulator_status = status
    print("Web server: Coffee device and simulator references set")

def start_web_server(host='0.0.0.0', port=5001):
    """Start the Flask web server in a separate thread."""
    def run_server():
        print(f"Starting web server at http://{host}:{port}")
        app.run(host=host, port=port, debug=False, use_reloader=False)
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    return server_thread

# HTML Templates
SETTINGS_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Coffee Machine Settings</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; color: #333; }
        .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden; }
        .header { background: linear-gradient(135deg, #6B4E3D, #8B6F47); color: white; padding: 30px; text-align: center; }
        .header h1 { margin: 0; font-size: 2.5em; font-weight: 300; }
        .status-info { display: flex; justify-content: space-between; margin-top: 15px; font-size: 1.1em; }
        .status-connected { color: #4CAF50; font-weight: bold; }
        .status-disconnected { color: #f44336; font-weight: bold; }
        .content { padding: 30px; }
        .navigation { text-align: center; margin-bottom: 30px; }
        .nav-link { color: #6B4E3D; text-decoration: none; margin: 0 15px; font-weight: 500; }
        .nav-link:hover { text-decoration: underline; }
        .settings-form { max-width: 800px; margin: 0 auto; }
        .settings-section { margin-bottom: 30px; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; }
        .section-header { background: #f8f9fa; padding: 15px 20px; border-bottom: 1px solid #e0e0e0; font-size: 1.3em; font-weight: 600; color: #495057; }
        .section-content { padding: 20px; }
        .form-group { margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #f0f0f0; }
        .form-group:last-child { border-bottom: none; }
        .form-label { flex: 1; font-weight: 500; color: #495057; margin-right: 20px; }
        .form-control { flex: 0 0 200px; padding: 8px 12px; border: 1px solid #ced4da; border-radius: 4px; font-size: 14px; }
        .form-control:focus { outline: none; border-color: #6B4E3D; box-shadow: 0 0 0 2px rgba(107, 78, 61, 0.2); }
        .checkbox-control { flex: 0 0 auto; }
        .datetime-control { flex: 0 0 250px; }
        .input-group { display: flex; align-items: center; gap: 10px; }
        .btn { background: #6B4E3D; color: white; border: none; padding: 12px 24px; border-radius: 5px; cursor: pointer; font-size: 16px; margin: 10px 5px; }
        .btn:hover { background: #5a3e2d; }
        .btn-secondary { background: #6c757d; }
        .btn-secondary:hover { background: #5a6268; }
        .btn-small { padding: 6px 12px; font-size: 12px; margin: 0; }
        .btn-send { background: #28a745; }
        .btn-send:hover { background: #218838; }
        .form-actions { text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0; }
        .alert { padding: 15px; margin-bottom: 20px; border: 1px solid transparent; border-radius: 4px; }
        .alert-success { color: #155724; background-color: #d4edda; border-color: #c3e6cb; }
        .alert-error { color: #721c24; background-color: #f8d7da; border-color: #f5c6cb; }
        .loading { display: none; text-align: center; padding: 20px; }
        .endpoint-path { font-family: 'Courier New', monospace; font-size: 12px; color: #6c757d; display: block; margin-top: 2px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚙️ Coffee Machine Settings</h1>
            <div class="status-info">
                <span>Connection: <span class="{{ 'status-connected' if connection_status == 'Connected' else 'status-disconnected' }}">{{ connection_status }}</span></span>
                <span>Last Updated: {{ current_time }}</span>
            </div>
        </div>
        
        <div class="content">
            <div class="navigation">
                <a href="/" class="nav-link">🏠 Control Panel</a>
                <a href="/status" class="nav-link">📊 Status Dashboard</a>
                <a href="/settings" class="nav-link">⚙️ Settings</a>
                <a href="/machine-interface" class="nav-link">🖥️ Machine Interface</a>
            </div>

            <div id="alert-container"></div>
            <div id="loading" class="loading"><p>Updating settings...</p></div>

            <form id="settings-form" class="settings-form">
                <div class="settings-section">
                    <div class="section-header">All Machine Settings</div>
                    <div class="section-content" id="all-settings"></div>
                </div>
                <div class="form-actions">
                    <button type="submit" class="btn">💾 Save Settings</button>
                    <button type="button" class="btn btn-secondary" onclick="loadCurrentSettings()">🔄 Load Current Values</button>
                    <button type="reset" class="btn btn-secondary">🗑️ Reset Form</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        const settingsMappings = [
            {endpoint: "/preinfusion/singleOnDurationGr1", type: "integer", label: "Single On Duration Group 1 (ms)", min: 0, max: 10000},
            {endpoint: "/power/group3ModeSetting", type: "integer", label: "Group 3 Mode Setting", min: 0, max: 10},
            {endpoint: "/power/ecoTimeout2", type: "integer", label: "Eco Timeout 2 (minutes)", min: 0, max: 1440},
            {endpoint: "/manteinance/waterFilterDuration", type: "integer", label: "Water Filter Duration (days)", min: 0, max: 365},
            {endpoint: "/autosteamer/washingTimeout", type: "integer", label: "Autosteamer Washing Timeout (seconds)", min: 0, max: 3600},
            {endpoint: "/ledBar/ecoLedLevel", type: "integer", label: "Eco LED Level", min: 0, max: 100},
            {endpoint: "/preinfusion/doubleOnDurationGr1", type: "integer", label: "Double On Duration Group 1 (ms)", min: 0, max: 10000},
            {endpoint: "/ledBar/ecoLedEnabled", type: "boolean", label: "Eco LED Enabled"},
            {endpoint: "/preinfusion/singleOnDurationGr3", type: "integer", label: "Single On Duration Group 3 (ms)", min: 0, max: 10000},
            {endpoint: "/display/userMenuConfig", type: "integer", label: "Display User Menu Config", min: 0, max: 100},
            {endpoint: "/doses/extraDoseEnabled", type: "boolean", label: "Extra Dose Enabled"},
            {endpoint: "/preinfusion/singleOffDurationGr1", type: "integer", label: "Single Off Duration Group 1 (ms)", min: 0, max: 10000},
            {endpoint: "/userSettings/boilerTempUserEnabled", type: "boolean", label: "Boiler Temp User Enabled"},
            {endpoint: "/doses/doseProgrammingEnabled", type: "boolean", label: "Dose Programming Enabled"},
            {endpoint: "/preinfusion/doubleOffDurationGr2", type: "integer", label: "Double Off Duration Group 2 (ms)", min: 0, max: 10000},
            {endpoint: "/machineSettings/password", type: "integer", label: "Password", min: 0, max: 9999},
            {endpoint: "/userSettings/groupsTempUserEnabled", type: "boolean", label: "Groups Temp User Enabled"},
            {endpoint: "/preinfusion/doubleOffDurationGr1", type: "integer", label: "Double Off Duration Group 1 (ms)", min: 0, max: 10000},
            {endpoint: "/machineSettings/cupHeatingRange", type: "integer", label: "Cup Heating Range", min: 0, max: 100},
            {endpoint: "/groupNumber", type: "integer", label: "Group Number", min: 1, max: 3},
            {endpoint: "/preinfusion/doubleEnabledGr2", type: "boolean", label: "Double Enabled Group 2"},
            {endpoint: "/power/ecoTimeout3", type: "integer", label: "Eco Timeout 3 (minutes)", min: 0, max: 1440},
            {endpoint: "/preinfusion/singleOffDurationGr2", type: "integer", label: "Single Off Duration Group 2 (ms)", min: 0, max: 10000},
            {endpoint: "/preinfusion/doubleOnDurationGr2", type: "integer", label: "Double On Duration Group 2 (ms)", min: 0, max: 10000},
            {endpoint: "/temperature/tempSetpointGr3", type: "integer", label: "Temperature Setpoint Group 3 (°C)", min: 80, max: 100},
            {endpoint: "/userSettings/userShortMenuEnabled", type: "boolean", label: "User Short Menu Enabled"},
            {endpoint: "/preinfusion/doubleOnDurationGr3", type: "integer", label: "Double On Duration Group 3 (ms)", min: 0, max: 10000},
            {endpoint: "/machineSettings/hartwallEnabled", type: "integer", label: "Hartwall Enabled", min: 0, max: 1},
            {endpoint: "/temperature/tempSetpointBoiler", type: "integer", label: "Temperature Setpoint Boiler (°C)", min: 80, max: 120},
            {endpoint: "/preinfusion/doubleOffDurationGr3", type: "integer", label: "Double Off Duration Group 3 (ms)", min: 0, max: 10000},
            {endpoint: "/ledBar/ecoLedTimeout", type: "integer", label: "Eco LED Timeout (seconds)", min: 0, max: 3600},
            {endpoint: "/preinfusion/singleOnDurationGr2", type: "integer", label: "Single On Duration Group 2 (ms)", min: 0, max: 10000},
            {endpoint: "/ledBar/ledBarEnabled", type: "boolean", label: "LED Bar Enabled"},
            {endpoint: "/machineSettings/language", type: "integer", label: "Language", min: 0, max: 10},
            {endpoint: "/temperature/tempSetpointGr2", type: "integer", label: "Temperature Setpoint Group 2 (°C)", min: 80, max: 100},
            {endpoint: "/info/installationDate", type: "datetime", label: "Installation Date"},
            {endpoint: "/autosteamer/washingDuration", type: "integer", label: "Autosteamer Washing Duration (seconds)", min: 0, max: 300},
            {endpoint: "/preinfusion/doubleEnabledGr3", type: "boolean", label: "Double Enabled Group 3"},
            {endpoint: "/power/group2ModeSetting", type: "integer", label: "Group 2 Mode Setting", min: 0, max: 10},
            {endpoint: "/power/ecoTimeout1", type: "integer", label: "Eco Timeout 1 (minutes)", min: 0, max: 1440},
            {endpoint: "/machineSettings/showMode", type: "boolean", label: "Show Mode"},
            {endpoint: "/machineSettings/teaCoffeeErogationEnabled", type: "boolean", label: "Tea Coffee Erogation Enabled"},
            {endpoint: "/preinfusion/singleEnabledGr3", type: "boolean", label: "Single Enabled Group 3"},
            {endpoint: "/machineSettings/erogationLoadEnabled", type: "boolean", label: "Erogation Load Enabled"},
            {endpoint: "/purge/duration", type: "integer", label: "Purge Duration (seconds)", min: 0, max: 300},
            {endpoint: "/purge/enabled", type: "boolean", label: "Purge Enabled"},
            {endpoint: "/machineSettings/manualWashingCycles", type: "integer", label: "Manual Washing Cycles", min: 0, max: 100},
            {endpoint: "/power/machineModeSetting", type: "integer", label: "Machine Mode Setting", min: 0, max: 10},
            {endpoint: "/preinfusion/preinfusionSingleEnabled", type: "boolean", label: "Preinfusion Single Enabled"},
            {endpoint: "/preinfusion/singleEnabledGr2", type: "boolean", label: "Single Enabled Group 2"},
            {endpoint: "/doses/continuosDoseEnabled", type: "boolean", label: "Continuous Dose Enabled"},
            {endpoint: "/preinfusion/singleOffDurationGr3", type: "integer", label: "Single Off Duration Group 3 (ms)", min: 0, max: 10000},
            {endpoint: "/autosteamer/enabled", type: "boolean", label: "Autosteamer Enabled"},
            {endpoint: "/machineSettings/automaticWashingCycles", type: "integer", label: "Automatic Washing Cycles", min: 0, max: 100},
            {endpoint: "/temperature/tempSetpointGr1", type: "integer", label: "Temperature Setpoint Group 1 (°C)", min: 80, max: 100},
            {endpoint: "/machineSettings/cupHeaterEnabled", type: "boolean", label: "Cup Heater Enabled"},
            {endpoint: "/manteinance/residualCoffeeForManteinance", type: "integer", label: "Residual Coffee For Maintenance", min: 0, max: 10000},
            {endpoint: "/machineSettings/probeSensitivity", type: "integer", label: "Probe Sensitivity", min: 0, max: 10},
            {endpoint: "/machineSettings/temperatureUnit", type: "integer", label: "Temperature Unit (0=°C, 1=°F)", min: 0, max: 1},
            {endpoint: "/fwVersion", type: "integer", label: "Firmware Version", min: 0, max: 999999},
            {endpoint: "/preinfusion/preinfusionDoubleEnabled", type: "boolean", label: "Preinfusion Double Enabled"},
            {endpoint: "/userSettings/preinfusionUserEnabled", type: "boolean", label: "Preinfusion User Enabled"},
            {endpoint: "/machineSettings/pressureUnit", type: "integer", label: "Pressure Unit", min: 0, max: 2}
        ];

        function generateSettingsForm() {
            const container = document.getElementById('all-settings');
            settingsMappings.forEach(setting => {
                const formGroup = document.createElement('div');
                formGroup.className = 'form-group';
                
                const label = document.createElement('label');
                label.className = 'form-label';
                label.innerHTML = setting.label + '<span class="endpoint-path">' + setting.endpoint + '</span>';
                
                // Create input group container
                const inputGroup = document.createElement('div');
                inputGroup.className = 'input-group';
                
                let input;
                if (setting.type === 'boolean') {
                    input = document.createElement('input');
                    input.type = 'checkbox';
                    input.className = 'checkbox-control';
                } else if (setting.type === 'datetime') {
                    input = document.createElement('input');
                    input.type = 'datetime-local';
                    input.className = 'form-control datetime-control';
                } else {
                    input = document.createElement('input');
                    input.type = 'number';
                    input.className = 'form-control';
                    if (setting.min !== undefined) input.min = setting.min;
                    if (setting.max !== undefined) input.max = setting.max;
                }
                
                input.name = setting.endpoint;
                
                // Create individual send button
                const sendButton = document.createElement('button');
                sendButton.type = 'button';
                sendButton.className = 'btn btn-small btn-send';
                sendButton.textContent = 'Send';
                sendButton.onclick = () => sendIndividualSetting(setting.endpoint, input, setting.type);
                
                // Add input and button to input group
                inputGroup.appendChild(input);
                inputGroup.appendChild(sendButton);
                
                formGroup.appendChild(label);
                formGroup.appendChild(inputGroup);
                container.appendChild(formGroup);
            });
        }

        function sendIndividualSetting(endpoint, inputElement, type) {
            let value;
            
            // Get value based on input type
            if (type === 'boolean') {
                value = inputElement.checked;
            } else if (type === 'datetime') {
                value = inputElement.value;
            } else {
                value = parseInt(inputElement.value) || 0;
            }
            
            // Create settings object with single setting
            const settings = {};
            settings[endpoint] = value;
            
            // Show loading state on the specific button
            const button = inputElement.nextElementSibling;
            const originalText = button.textContent;
            button.textContent = 'Sending...';
            button.disabled = true;
            
            fetch('/api/update_settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(settings)
            })
            .then(response => response.json())
            .then(data => {
                button.textContent = originalText;
                button.disabled = false;
                
                if (data.success) {
                    showAlert(`Setting ${endpoint} updated successfully`, 'success');
                    // Briefly highlight the button as success
                    button.style.background = '#28a745';
                    setTimeout(() => {
                        button.style.background = '';
                    }, 1000);
                } else {
                    showAlert(`Failed to update ${endpoint}: ${data.error || 'Unknown error'}`, 'error');
                }
            })
            .catch(error => {
                button.textContent = originalText;
                button.disabled = false;
                showAlert(`Error updating ${endpoint}: ${error.message}`, 'error');
            });
        }

        function showAlert(message, type) {
            const alertContainer = document.getElementById('alert-container');
            const alert = document.createElement('div');
            alert.className = 'alert alert-' + type;
            alert.textContent = message;
            alertContainer.innerHTML = '';
            alertContainer.appendChild(alert);
            setTimeout(() => alert.remove(), 5000);
        }

        function loadCurrentSettings() {
            // Load current settings from the server
            fetch('/api/get_current_settings')
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.settings) {
                        populateFormWithSettings(data.settings);
                        showAlert('Current settings loaded successfully', 'success');
                    } else {
                        showAlert('No current settings available - you can still configure and save new settings', 'success');
                    }
                })
                .catch(error => {
                    showAlert('Could not load current settings - you can still configure and save new settings', 'success');
                });
        }

        function populateFormWithSettings(settings) {
            // Populate form fields with current settings
            settingsMappings.forEach(setting => {
                const input = document.querySelector(`input[name="${setting.endpoint}"]`);
                if (input && settings.data) {
                    // Navigate through nested object structure to find the value
                    const pathParts = setting.endpoint.substring(1).split('/');
                    let value = settings.data;
                    
                    for (const part of pathParts) {
                        if (value && typeof value === 'object' && part in value) {
                            value = value[part];
                        } else {
                            value = null;
                            break;
                        }
                    }
                    
                    if (value !== null) {
                        if (setting.type === 'boolean') {
                            input.checked = Boolean(value);
                        } else if (setting.type === 'datetime') {
                            if (value) {
                                // Convert ISO string to datetime-local format
                                const date = new Date(value);
                                const localDateTime = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
                                    .toISOString().slice(0, 16);
                                input.value = localDateTime;
                            }
                        } else {
                            input.value = value;
                        }
                    }
                }
            });
        }

        document.getElementById('settings-form').addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            const settings = {};
            
            for (let [key, value] of formData.entries()) {
                const setting = settingsMappings.find(s => s.endpoint === key);
                if (setting) {
                    if (setting.type === 'boolean') {
                        settings[key] = true;
                    } else if (setting.type === 'datetime') {
                        settings[key] = value;
                    } else {
                        settings[key] = parseInt(value) || 0;
                    }
                }
            }
            
            // Handle unchecked checkboxes
            settingsMappings.forEach(setting => {
                if (setting.type === 'boolean' && !formData.has(setting.endpoint)) {
                    settings[setting.endpoint] = false;
                }
            });
            
            document.getElementById('loading').style.display = 'block';
            
            fetch('/api/update_settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(settings)
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('loading').style.display = 'none';
                if (data.success) {
                    showAlert(data.message, 'success');
                } else {
                    showAlert(data.error || 'Failed to update settings', 'error');
                }
            })
            .catch(error => {
                document.getElementById('loading').style.display = 'none';
                showAlert('Error: ' + error.message, 'error');
            });
        });

        // Generate form and load current settings on page load
        document.addEventListener('DOMContentLoaded', function() {
            generateSettingsForm();
            // Automatically load current settings when page loads
            setTimeout(loadCurrentSettings, 500); // Small delay to ensure form is generated
        });
    </script>
</body>
</html>
"""

MACHINE_INTERFACE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Coffee Machine Interface</title>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background-color: #f5f5f5; 
            color: #333; 
        }
        .page-container { 
            max-width: 1200px; 
            margin: 0 auto; 
            background: white; 
            border-radius: 10px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
            overflow: hidden; 
        }
        .header { 
            background: linear-gradient(135deg, #6B4E3D, #8B6F47); 
            color: white; 
            padding: 30px; 
            text-align: center; 
        }
        .header h1 { 
            margin: 0; 
            font-size: 2.5em; 
            font-weight: 300; 
        }
        .status-info { 
            display: flex; 
            justify-content: space-between; 
            margin-top: 15px; 
            font-size: 1.1em; 
        }
        .status-connected { 
            color: #4CAF50; 
            font-weight: bold; 
        }
        .status-disconnected { 
            color: #f44336; 
            font-weight: bold; 
        }
        .content { 
            padding: 30px; 
        }
        .navigation { 
            text-align: center; 
            margin-bottom: 30px; 
        }
        .nav-link { 
            color: #6B4E3D; 
            text-decoration: none; 
            margin: 0 15px; 
            font-weight: 500; 
        }
        .nav-link:hover { 
            text-decoration: underline; 
        }
        
        /* Machine Interface Styles */
        .machine-container {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 60vh;
            background-color: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
        }
        
        .interface-container {
            display: flex;
            gap: 40px;
            flex-wrap: wrap;
            justify-content: center;
        }
        
        .group {
            text-align: center;
            margin: 20px;
        }
        
        .group h2 {
            color: #6B4E3D;
            margin-bottom: 20px;
            font-size: 1.5em;
        }
        
        .dial {
            position: relative;
            width: 250px;
            height: 250px;
            border-radius: 50%;
            background-color: #333;
            border: 10px solid #555;
            display: flex;
            justify-content: center;
            align-items: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        }
        
        .center-display {
            width: 120px;
            height: 120px;
            background-color: #000;
            border-radius: 50%;
            color: #00ff00;
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 14px;
            font-weight: bold;
            border: 10px solid #ccc;
            text-align: center;
            line-height: 1.2;
        }
        
        .button {
            position: absolute;
            width: 50px;
            height: 50px;
            background-color: #6B4E3D;
            color: white;
            border-radius: 8px;
            display: flex;
            justify-content: center;
            align-items: center;
            cursor: pointer;
            font-weight: bold;
            user-select: none;
            transition: all 0.2s ease;
            border: 2px solid #8B6F47;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }
        
        .button:hover {
            background-color: #8B6F47;
            transform: scale(1.1);
        }
        
        .button:active {
            background-color: #5a3e2d;
            transform: scale(0.95);
        }
        
        .button.k1 {
            transform: rotate(0deg) translate(100px) rotate(0deg);
        }
        
        .button.k2 {
            transform: rotate(51.4deg) translate(100px) rotate(-51.4deg);
        }
        
        .button.k3 {
            transform: rotate(102.8deg) translate(100px) rotate(-102.8deg);
        }
        
        .button.k4 {
            transform: rotate(154.2deg) translate(100px) rotate(-154.2deg);
        }
        
        .button.k5 {
            transform: rotate(205.6deg) translate(100px) rotate(-205.6deg);
        }
        
        .button.k6 {
            transform: rotate(257deg) translate(100px) rotate(-257deg);
        }
        
        .button.k7 {
            transform: rotate(308.4deg) translate(100px) rotate(-308.4deg);
        }
        
        .button.k1:hover { transform: rotate(0deg) translate(100px) rotate(0deg) scale(1.1); }
        .button.k2:hover { transform: rotate(51.4deg) translate(100px) rotate(-51.4deg) scale(1.1); }
        .button.k3:hover { transform: rotate(102.8deg) translate(100px) rotate(-102.8deg) scale(1.1); }
        .button.k4:hover { transform: rotate(154.2deg) translate(100px) rotate(-154.2deg) scale(1.1); }
        .button.k5:hover { transform: rotate(205.6deg) translate(100px) rotate(-205.6deg) scale(1.1); }
        .button.k6:hover { transform: rotate(257deg) translate(100px) rotate(-257deg) scale(1.1); }
        .button.k7:hover { transform: rotate(308.4deg) translate(100px) rotate(-308.4deg) scale(1.1); }
        
        .button.k1:active { transform: rotate(0deg) translate(100px) rotate(0deg) scale(0.95); }
        .button.k2:active { transform: rotate(51.4deg) translate(100px) rotate(-51.4deg) scale(0.95); }
        .button.k3:active { transform: rotate(102.8deg) translate(100px) rotate(-102.8deg) scale(0.95); }
        .button.k4:active { transform: rotate(154.2deg) translate(100px) rotate(-154.2deg) scale(0.95); }
        .button.k5:active { transform: rotate(205.6deg) translate(100px) rotate(-205.6deg) scale(0.95); }
        .button.k6:active { transform: rotate(257deg) translate(100px) rotate(-257deg) scale(0.95); }
        .button.k7:active { transform: rotate(308.4deg) translate(100px) rotate(-308.4deg) scale(0.95); }
        
        @media (max-width: 768px) {
            .interface-container {
                flex-direction: column;
                gap: 20px;
            }
            
            .dial {
                width: 200px;
                height: 200px;
            }
            
            .center-display {
                width: 100px;
                height: 100px;
                font-size: 12px;
            }
            
            .button {
                width: 40px;
                height: 40px;
                font-size: 12px;
            }
            
            .button.k1 { transform: rotate(0deg) translate(80px) rotate(0deg); }
            .button.k2 { transform: rotate(51.4deg) translate(80px) rotate(-51.4deg); }
            .button.k3 { transform: rotate(102.8deg) translate(80px) rotate(-102.8deg); }
            .button.k4 { transform: rotate(154.2deg) translate(80px) rotate(-154.2deg); }
            .button.k5 { transform: rotate(205.6deg) translate(80px) rotate(-205.6deg); }
            .button.k6 { transform: rotate(257deg) translate(80px) rotate(-257deg); }
            .button.k7 { transform: rotate(308.4deg) translate(80px) rotate(-308.4deg); }
        }
    </style>
</head>
<body>
    <div class="page-container">
        <div class="header">
            <h1>🖥️ Coffee Machine Interface</h1>
            <div class="status-info">
                <span>Connection: <span class="{{ 'status-connected' if connection_status == 'Connected' else 'status-disconnected' }}">{{ connection_status }}</span></span>
                <span>Last Updated: {{ current_time }}</span>
            </div>
        </div>
        
        <div class="content">
            <div class="navigation">
                <a href="/" class="nav-link">🏠 Control Panel</a>
                <a href="/status" class="nav-link">📊 Status Dashboard</a>
                <a href="/settings" class="nav-link">⚙️ Settings</a>
                <a href="/machine-interface" class="nav-link">🖥️ Machine Interface</a>
            </div>

            <div class="machine-container">
                <div class="interface-container">
                    <div class="group">
                        <h2>Group 1</h2>
                        <div class="dial">
                            <div class="center-display">
                                <span id="group1-display">Ready</span>
                            </div>
                            <div class="button k1" data-group="1" data-coffee="1">K1</div>
                            <div class="button k2" data-group="1" data-coffee="2">K2</div>
                            <div class="button k3" data-group="1" data-coffee="3">K3</div>
                            <div class="button k4" data-group="1" data-coffee="4">K4</div>
                            <div class="button k5" data-group="1" data-coffee="5">K5</div>
                            <div class="button k6" data-group="1" data-coffee="6">K6</div>
                            <div class="button k7" data-group="1" data-coffee="7">K7</div>
                        </div>
                    </div>
                    <div class="group">
                        <h2>Group 2</h2>
                        <div class="dial">
                            <div class="center-display">
                                <span id="group2-display">Ready</span>
                            </div>
                            <div class="button k1" data-group="2" data-coffee="1">K1</div>
                            <div class="button k2" data-group="2" data-coffee="2">K2</div>
                            <div class="button k3" data-group="2" data-coffee="3">K3</div>
                            <div class="button k4" data-group="2" data-coffee="4">K4</div>
                            <div class="button k5" data-group="2" data-coffee="5">K5</div>
                            <div class="button k6" data-group="2" data-coffee="6">K6</div>
                            <div class="button k7" data-group="2" data-coffee="7">K7</div>
                        </div>
                    </div>
                    <div class="group">
                        <h2>Group 3</h2>
                        <div class="dial">
                            <div class="center-display">
                                <span id="group3-display">Ready</span>
                            </div>
                            <div class="button k1" data-group="3" data-coffee="1">K1</div>
                            <div class="button k2" data-group="3" data-coffee="2">K2</div>
                            <div class="button k3" data-group="3" data-coffee="3">K3</div>
                            <div class="button k4" data-group="3" data-coffee="4">K4</div>
                            <div class="button k5" data-group="3" data-coffee="5">K5</div>
                            <div class="button k6" data-group="3" data-coffee="6">K6</div>
                            <div class="button k7" data-group="3" data-coffee="7">K7</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const groups = document.querySelectorAll('.group');
            const timers = {};

            groups.forEach((group, groupIndex) => {
                const display = group.querySelector('.center-display span');
                const buttons = group.querySelectorAll('.button');
                const groupNum = groupIndex + 1;

                buttons.forEach(button => {
                    button.addEventListener('click', () => {
                        const buttonId = button.textContent;
                        const coffeeType = button.getAttribute('data-coffee');
                        const groupId = button.getAttribute('data-group');

                        // Clear any existing timer for this group
                        if (timers[groupNum]) {
                            clearInterval(timers[groupNum]);
                        }

                        // Show brewing in progress
                        display.textContent = `Brewing ${buttonId}...`;

                        // Send the coffee brewing request to the server
                        fetch('/api/brew_coffee', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                coffee_type: parseInt(coffeeType),
                                group: `group${groupId}`
                            })
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                console.log(`Coffee ${buttonId} brewed successfully on Group ${groupId}`);
                                // Display the brewed coffee and duration
                                if (data.brewing_info) {
                                    display.textContent = `${buttonId}: ${data.brewing_info.duration}ms`;
                                } else {
                                    display.textContent = `${buttonId}: Brewed`;
                                }
                                
                                // Clear display after 5 seconds
                                setTimeout(() => {
                                    display.textContent = 'Ready';
                                }, 5000);
                            } else {
                                console.error(`Failed to brew coffee: ${data.error}`);
                                display.textContent = 'Error';
                                setTimeout(() => {
                                    display.textContent = 'Ready';
                                }, 3000);
                            }
                        })
                        .catch(error => {
                            console.error('Error brewing coffee:', error);
                            display.textContent = 'Error';
                            setTimeout(() => {
                                display.textContent = 'Ready';
                            }, 3000);
                        });
                    });
                });
            });
        });
    </script>
</body>
</html>
"""

STATUS_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Coffee Machine Status</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; color: #333; }
        .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden; }
        .header { background: linear-gradient(135deg, #6B4E3D, #8B6F47); color: white; padding: 30px; text-align: center; }
        .header h1 { margin: 0; font-size: 2.5em; font-weight: 300; }
        .status-info { display: flex; justify-content: space-between; margin-top: 15px; font-size: 1.1em; }
        .status-connected { color: #4CAF50; font-weight: bold; }
        .status-disconnected { color: #f44336; font-weight: bold; }
        .content { padding: 30px; }
        .navigation { text-align: center; margin-bottom: 20px; }
        .nav-link { color: #6B4E3D; text-decoration: none; margin: 0 15px; font-weight: 500; }
        .nav-link:hover { text-decoration: underline; }
        .section { margin-bottom: 40px; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; }
        .section-header { background: #f8f9fa; padding: 15px 20px; border-bottom: 1px solid #e0e0e0; font-size: 1.3em; font-weight: 600; color: #495057; }
        .section-content { padding: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 6px; padding: 15px; }
        .card-title { font-weight: 600; color: #495057; margin-bottom: 10px; font-size: 1.1em; }
        .data-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        .data-table th, .data-table td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #dee2e6; }
        .data-table th { background: #e9ecef; font-weight: 600; color: #495057; }
        .data-table tr:hover { background: #f8f9fa; }
        .value { font-family: 'Courier New', monospace; background: #e9ecef; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }
        .timestamp { color: #6c757d; font-size: 0.85em; }
        .no-data { color: #6c757d; font-style: italic; text-align: center; padding: 20px; }
        .refresh-btn { background: #6B4E3D; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-size: 1em; margin-bottom: 20px; }
        .refresh-btn:hover { background: #5a3e2d; }
    </style>
    <script>
        setTimeout(function() { location.reload(); }, 60000);
        let countdown = 60;
        function updateCountdown() {
            const countdownElement = document.getElementById('countdown');
            if (countdownElement) {
                countdownElement.textContent = countdown;
                countdown--;
                if (countdown < 0) countdown = 60;
            }
        }
        setInterval(updateCountdown, 1000);
        window.onload = function() { updateCountdown(); };
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>☕ Coffee Machine Status Dashboard</h1>
            <div style="margin-top: 10px; font-size: 1.1em; color: #4CAF50; font-weight: bold;">📍 Reading from LOCAL Simulator Data</div>
            <div class="status-info">
                <span>Connection: <span class="{{ 'status-connected' if connection_status == 'Connected' else 'status-disconnected' }}">{{ connection_status }}</span></span>
                <span>Last Updated: {{ current_time }}</span>
                <span>Auto-refresh in: <span id="countdown" style="font-weight: bold; color: #4CAF50;">60</span>s</span>
            </div>
        </div>
        
        <div class="content">
            <div class="navigation">
                <a href="/" class="nav-link">🏠 Control Panel</a>
                <a href="/status" class="nav-link">📊 Status Dashboard</a>
                <a href="/settings" class="nav-link">⚙️ Settings</a>
                <a href="/machine-interface" class="nav-link">🖥️ Machine Interface</a>
                <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
            </div>

            <div class="section">
                <div class="section-header">☕ Coffee Counters</div>
                <div class="section-content">
                    {% if counters and counters.data %}
                        <div class="grid">
                            {% for group_name, group_data in counters.data.items() %}
                                <div class="card">
                                    <div class="card-title">{{ group_name.title() }}</div>
                                    <table class="data-table">
                                        <thead><tr><th>Coffee Type</th><th>Count</th><th>Last Updated</th></tr></thead>
                                        <tbody>
                                            {% for coffee_type, data in group_data.items() %}
                                                <tr>
                                                    <td>{{ coffee_type.upper() }}</td>
                                                    <td><span class="value">{{ data.value if data.value is not none else 'N/A' }}</span></td>
                                                    <td class="timestamp">{{ data.timestamp[:19] if data.timestamp else 'N/A' }}</td>
                                                </tr>
                                            {% endfor %}
                                        </tbody>
                                    </table>
                                </div>
                            {% endfor %}
                        </div>
                    {% else %}
                        <div class="no-data">No counter data available</div>
                    {% endif %}
                </div>
            </div>

            <div class="section">
                <div class="section-header">⚙️ Machine Settings</div>
                <div class="section-content">
                    {% if settings and settings.data %}
                        <div class="grid">
                            {% for category, category_data in settings.data.items() %}
                                <div class="card">
                                    <div class="card-title">{{ category.title().replace('_', ' ') }}</div>
                                    <table class="data-table">
                                        <thead><tr><th>Setting</th><th>Value</th></tr></thead>
                                        <tbody>
                                            {% for setting_name, value in category_data.items() %}
                                                <tr>
                                                    <td>{{ setting_name.replace('_', ' ').title() }}</td>
                                                    <td><span class="value">{{ value if value is not none else 'N/A' }}</span></td>
                                                </tr>
                                            {% endfor %}
                                        </tbody>
                                    </table>
                                </div>
                            {% endfor %}
                        </div>
                    {% else %}
                        <div class="no-data">No settings data available</div>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

ERROR_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error - Coffee Machine</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; color: #333; }
        .container { max-width: 800px; margin: 0 auto; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); padding: 40px; text-align: center; }
        .error-icon { font-size: 4em; color: #f44336; margin-bottom: 20px; }
        .error-title { font-size: 2em; color: #f44336; margin-bottom: 20px; }
        .error-message { font-size: 1.2em; color: #666; margin-bottom: 30px; padding: 20px; background: #f8f9fa; border-radius: 5px; border-left: 4px solid #f44336; }
        .back-link { color: #6B4E3D; text-decoration: none; font-weight: 500; font-size: 1.1em; }
        .back-link:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <div class="error-icon">⚠️</div>
        <div class="error-title">Error Loading Page</div>
        <div class="error-message">{{ error }}</div>
        <a href="/" class="back-link">← Back to Control Panel</a>
    </div>
</body>
</html>
"""

if __name__ == '__main__':
    # For standalone testing
    app.run(host='0.0.0.0', port=5000, debug=True)
