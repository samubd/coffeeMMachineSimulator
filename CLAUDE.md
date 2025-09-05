# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Coffee Machine Simulator for Astarte IoT platform that simulates a 3-group coffee machine. The simulator connects to Astarte via MQTT, sends telemetry data, handles commands, and includes a Flask web interface for control.

## Key Architecture Components

### Core Modules
- `coffee_machine_simulator.py` - Main simulator class with 3 coffee groups, alarm system, and brewing logic
- `main_new.py` - Primary entry point that connects to Astarte and starts the simulator
- `web_server.py` - Flask web interface for manual control and monitoring
- `astarte_api_client_fixed.py` - Network-resilient API client using urllib (replaces requests to avoid connection pooling issues)

### Configuration & Data
- `config.toml` - Astarte connection configuration (DEVICE_ID, REALM, CREDENTIALS_SECRET, PAIRING_URL)
- `status.json` - Persistent simulator state (alarms, counters, settings)
- `interfaces/` - Astarte interface definitions (JSON files defining data schemas)

### API Utilities
- `getCurrentAlarms.py`, `getCurrentCounters.py`, `getCurrentDoses.py`, etc. - Individual API endpoint scripts

## Running the Application

### Installation
```bash
pip install -r requirements.txt
```

### Main Application
```bash
python main_new.py
```

### Web Interface (if running separately)
```bash
python web_server.py
```
The web interface runs on port 5000 and provides manual controls for:
- Coffee brewing simulation
- Alarm management
- Settings updates
- Status monitoring

## Key Technical Details

### Network Resilience
This project uses a custom API client (`astarte_api_client_fixed.py`) that replaces the standard `requests` library with `urllib` to avoid TCP connection pooling issues that were causing system-level network failures.

### Astarte Integration
- Device connects via MQTT to Astarte IoT platform
- Implements multiple interfaces for telemetry, alarms, settings, and counters
- Supports both server-to-device and device-to-server data flows
- Persistent state management for reliability

### Simulator Features
- 3 independent coffee groups with realistic brewing cycles
- Comprehensive alarm system (critical, major blocking, major non-blocking, minor)
- Daily washing cycles and maintenance tracking
- Random coffee brewing with configurable parameters
- Real-time telemetry data transmission

## Configuration Notes

Before running, update `config.toml` with your Astarte instance details:
- DEVICE_ID: Your registered device ID
- REALM: Astarte realm name
- CREDENTIALS_SECRET: Device credentials
- PAIRING_URL: Astarte pairing endpoint

The simulator maintains state in `status.json` and will resume from the last known state on restart.