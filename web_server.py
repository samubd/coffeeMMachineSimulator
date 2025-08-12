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
                coffee_device.send(
                    "it.d8pro.device.Settings03",
                    path,
                    value,
                    timestamp=current_time
                )
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
        success = manual_brew_coffee(coffee_type, group)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Coffee K{coffee_type} brewed successfully on {group}'
            })
        else:
            return jsonify({'error': 'Failed to brew coffee'}), 500
            
    except Exception as e:
        print(f"Error in brew_coffee: {e}")
        return jsonify({'error': str(e)}), 500

def manual_brew_coffee(coffee_type: int, group: str = "group1") -> bool:
    """Manually brew a specific coffee type on a specific group."""
    try:
        if not coffee_device or not coffee_device.is_connected():
            return False
        
        # Generate coffee data using recipe-based erogation time
        erog_time = _get_erog_time_for_coffee_type(group, coffee_type)
        flow_total = random.randint(300, 600)
        
        current_time = datetime.now(ZoneInfo("Europe/Rome"))
        
        print(f"Manual brewing coffee: group={group}, type={coffee_type}, erogTime={erog_time}, flowTotal={flow_total}")
        
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
        
        return True
        
    except Exception as e:
        print(f"Error in manual_brew_coffee: {e}")
        return False

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

def start_web_server(host='localhost', port=5000):
    """Start the Flask web server in a separate thread."""
    def run_server():
        print(f"Starting web server at http://{host}:{port}")
        app.run(host=host, port=port, debug=False, use_reloader=False)
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    return server_thread

# HTML Templates
STATUS_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Coffee Machine Status</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }
        .container {
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
        .section {
            margin-bottom: 40px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden;
        }
        .section-header {
            background: #f8f9fa;
            padding: 15px 20px;
            border-bottom: 1px solid #e0e0e0;
            font-size: 1.3em;
            font-weight: 600;
            color: #495057;
        }
        .section-content {
            padding: 20px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        .card {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            padding: 15px;
        }
        .card-title {
            font-weight: 600;
            color: #495057;
            margin-bottom: 10px;
            font-size: 1.1em;
        }
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        .data-table th,
        .data-table td {
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }
        .data-table th {
            background: #e9ecef;
            font-weight: 600;
            color: #495057;
        }
        .data-table tr:hover {
            background: #f8f9fa;
        }
        .value {
            font-family: 'Courier New', monospace;
            background: #e9ecef;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.9em;
        }
        .timestamp {
            color: #6c757d;
            font-size: 0.85em;
        }
        .no-data {
            color: #6c757d;
            font-style: italic;
            text-align: center;
            padding: 20px;
        }
        .refresh-btn {
            background: #6B4E3D;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 1em;
            margin-bottom: 20px;
        }
        .refresh-btn:hover {
            background: #5a3e2d;
        }
        .navigation {
            text-align: center;
            margin-bottom: 20px;
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
    </style>
    <script>
        // Auto-refresh the page every 60 seconds
        setTimeout(function() {
            location.reload();
        }, 60000); // 60 seconds = 60000 milliseconds
        
        // Show a countdown timer for next refresh
        let countdown = 60;
        function updateCountdown() {
            const countdownElement = document.getElementById('countdown');
            if (countdownElement) {
                countdownElement.textContent = countdown;
                countdown--;
                if (countdown < 0) {
                    countdown = 60; // Reset for next cycle
                }
            }
        }
        
        // Update countdown every second
        setInterval(updateCountdown, 1000);
        
        // Initialize countdown when page loads
        window.onload = function() {
            updateCountdown();
        };
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>☕ Coffee Machine Status Dashboard</h1>
            <div style="margin-top: 10px; font-size: 1.1em; color: #4CAF50; font-weight: bold;">
                📍 Reading from LOCAL Simulator Data
            </div>
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
                <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
            </div>

            <!-- Coffee Counters Section -->
            <div class="section">
                <div class="section-header">☕ Coffee Counters</div>
                <div class="section-content">
                    {% if counters and counters.data %}
                        <div class="grid">
                            {% for group_name, group_data in counters.data.items() %}
                                <div class="card">
                                    <div class="card-title">{{ group_name.title() }}</div>
                                    <table class="data-table">
                                        <thead>
                                            <tr>
                                                <th>Coffee Type</th>
                                                <th>Count</th>
                                                <th>Last Updated</th>
                                            </tr>
                                        </thead>
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

            <!-- Settings Section -->
            <div class="section">
                <div class="section-header">⚙️ Machine Settings</div>
                <div class="section-content">
                    {% if settings and settings.data %}
                        <div class="grid">
                            {% for category, category_data in settings.data.items() %}
                                <div class="card">
                                    <div class="card-title">{{ category.title().replace('_', ' ') }}</div>
                                    <table class="data-table">
                                        <thead>
                                            <tr>
                                                <th>Setting</th>
                                                <th>Value</th>
                                            </tr>
                                        </thead>
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

            <!-- Doses Section -->
            <div class="section">
                <div class="section-header">💧 Coffee Doses</div>
                <div class="section-content">
                    {% if doses and doses.data %}
                        <div class="grid">
                            {% for group_name, group_data in doses.data.items() %}
                                <div class="card">
                                    <div class="card-title">{{ group_name.title() }}</div>
                                    <table class="data-table">
                                        <thead>
                                            <tr>
                                                <th>Coffee Type</th>
                                                <th>Dose (ml)</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {% for dose_type, dose_data in group_data.items() %}
                                                <tr>
                                                    <td>{{ dose_type.upper() }}</td>
                                                    <td><span class="value">{{ dose_data.value if dose_data.value is not none else 'N/A' }}</span></td>
                                                </tr>
                                            {% endfor %}
                                        </tbody>
                                    </table>
                                </div>
                            {% endfor %}
                        </div>
                    {% else %}
                        <div class="no-data">No doses data available</div>
                    {% endif %}
                </div>
            </div>

            <!-- Recipes Section -->
            <div class="section">
                <div class="section-header">📋 Coffee Recipes</div>
                <div class="section-content">
                    {% if recipes %}
                        <div class="grid">
                            {% for group_name, recipe_data in recipes.items() %}
                                <div class="card">
                                    <div class="card-title">{{ group_name.title() }}</div>
                                    {% if recipe_data %}
                                        <table class="data-table">
                                            <thead>
                                                <tr>
                                                    <th>Parameter</th>
                                                    <th>Value</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {% for param_name, param_value in recipe_data.items() %}
                                                    <tr>
                                                        <td>{{ param_name.replace('_', ' ').title() }}</td>
                                                        <td>
                                                            {% if param_value is mapping %}
                                                                <div style="font-size: 0.9em;">
                                                                    {% for k, v in param_value.items() %}
                                                                        <div>{{ k }}: <span class="value">{{ v }}</span></div>
                                                                    {% endfor %}
                                                                </div>
                                                            {% else %}
                                                                <span class="value">{{ param_value if param_value is not none else 'N/A' }}</span>
                                                            {% endif %}
                                                        </td>
                                                    </tr>
                                                {% endfor %}
                                            </tbody>
                                        </table>
                                    {% else %}
                                        <div class="no-data">No recipe data for this group</div>
                                    {% endif %}
                                </div>
                            {% endfor %}
                        </div>
                    {% else %}
                        <div class="no-data">No recipes data available</div>
                    {% endif %}
                </div>
            </div>

            <!-- Simulator Status Section -->
            <div class="section">
                <div class="section-header">🤖 Simulator Status</div>
                <div class="section-content">
                    {% if simulator_status %}
                        <div class="card">
                            <div class="card-title">Current Simulator State</div>
                            <table class="data-table">
                                <thead>
                                    <tr>
                                        <th>Component</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td>Counters Loaded</td>
                                        <td><span class="value">{{ 'Yes' if simulator_status.counters else 'No' }}</span></td>
                                    </tr>
                                    <tr>
                                        <td>Settings Loaded</td>
                                        <td><span class="value">{{ 'Yes' if simulator_status.settings else 'No' }}</span></td>
                                    </tr>
                                    <tr>
                                        <td>Doses Loaded</td>
                                        <td><span class="value">{{ 'Yes' if simulator_status.doses else 'No' }}</span></td>
                                    </tr>
                                    <tr>
                                        <td>Recipes Loaded</td>
                                        <td><span class="value">{{ 'Yes' if simulator_status.recipes else 'No' }}</span></td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    {% else %}
                        <div class="no-data">Simulator status not available</div>
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
    <title>Error - Coffee Machine Status</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 40px;
            text-align: center;
        }
        .error-icon {
            font-size: 4em;
            color: #f44336;
            margin-bottom: 20px;
        }
        .error-title {
            font-size: 2em;
            color: #f44336;
            margin-bottom: 20px;
        }
        .error-message {
            font-size: 1.2em;
            color: #666;
            margin-bottom: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 5px;
            border-left: 4px solid #f44336;
        }
        .back-link {
            color: #6B4E3D;
            text-decoration: none;
            font-weight: 500;
            font-size: 1.1em;
        }
        .back-link:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="error-icon">⚠️</div>
        <div class="error-title">Error Loading Status</div>
        <div class="error-message">{{ error }}</div>
        <a href="/" class="back-link">← Back to Control Panel</a>
    </div>
</body>
</html>
"""

if __name__ == '__main__':
    # For standalone testing
    app.run(host='localhost', port=5000, debug=True)
