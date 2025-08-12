"""
Network Diagnostic and Recovery Tool

This script helps diagnose and potentially recover from network issues
caused by corrupted connection states.
"""

import subprocess
import socket
import time
import sys
import os


def run_command(command, description):
    """Run a system command and return the result."""
    print(f"\n--- {description} ---")
    print(f"Running: {command}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"Output:\n{result.stdout}")
        if result.stderr:
            print(f"Error:\n{result.stderr}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("Command timed out")
        return False
    except Exception as e:
        print(f"Error running command: {e}")
        return False


def test_connectivity(host, port=443):
    """Test basic TCP connectivity to a host."""
    print(f"\n--- Testing connectivity to {host}:{port} ---")
    try:
        # Test DNS resolution
        ip = socket.gethostbyname(host)
        print(f"DNS resolution: {host} -> {ip}")
        
        # Test TCP connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        start_time = time.time()
        result = sock.connect_ex((host, port))
        end_time = time.time()
        sock.close()
        
        if result == 0:
            print(f"✅ TCP connection successful ({end_time - start_time:.2f}s)")
            return True
        else:
            print(f"❌ TCP connection failed with code {result}")
            return False
            
    except socket.gaierror as e:
        print(f"❌ DNS resolution failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False


def diagnose_network_state():
    """Diagnose current network state."""
    print("=== NETWORK DIAGNOSTIC TOOL ===")
    
    # Test basic connectivity first
    host = 'services.sanremomachines.com'
    connectivity_ok = test_connectivity(host)
    
    # Show network statistics
    run_command("netstat -an | findstr :443", "Active HTTPS connections")
    run_command("netstat -an | findstr services.sanremomachines.com", "Connections to target server")
    
    # Show DNS cache
    run_command("ipconfig /displaydns | findstr services.sanremomachines.com", "DNS cache for target server")
    
    # Show network adapter status
    run_command("ipconfig /all", "Network adapter configuration")
    
    return connectivity_ok


def attempt_network_recovery():
    """Attempt to recover from network issues."""
    print("\n=== ATTEMPTING NETWORK RECOVERY ===")
    
    # Flush DNS cache
    success1 = run_command("ipconfig /flushdns", "Flushing DNS cache")
    
    # Release and renew IP
    success2 = run_command("ipconfig /release", "Releasing IP address")
    time.sleep(2)
    success3 = run_command("ipconfig /renew", "Renewing IP address")
    
    # Reset TCP/IP stack
    success4 = run_command("netsh int ip reset", "Resetting TCP/IP stack")
    
    # Reset Winsock catalog
    success5 = run_command("netsh winsock reset", "Resetting Winsock catalog")
    
    print(f"\nRecovery steps completed:")
    print(f"  DNS flush: {'✅' if success1 else '❌'}")
    print(f"  IP release: {'✅' if success2 else '❌'}")
    print(f"  IP renew: {'✅' if success3 else '❌'}")
    print(f"  TCP/IP reset: {'✅' if success4 else '❌'}")
    print(f"  Winsock reset: {'✅' if success5 else '❌'}")
    
    if success4 or success5:
        print("\n⚠️  Some changes require a system restart to take effect.")
        print("Consider restarting your computer if connectivity issues persist.")


def main():
    """Main diagnostic and recovery function."""
    print("Network Diagnostic and Recovery Tool")
    print("This tool helps diagnose and fix network connectivity issues.")
    
    # Check if running as administrator (Windows)
    try:
        import ctypes
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        # Fallback - assume not admin
        is_admin = False
    
    if not is_admin:
        print("\n⚠️  Warning: Not running as administrator.")
        print("Some recovery commands may fail without admin privileges.")
    
    # Initial diagnosis
    connectivity_ok = diagnose_network_state()
    
    if not connectivity_ok:
        print(f"\n❌ Connectivity to services.sanremomachines.com is currently broken.")
        
        response = input("\nAttempt network recovery? (y/n): ").lower().strip()
        if response == 'y':
            attempt_network_recovery()
            
            # Test again after recovery
            print("\n=== TESTING CONNECTIVITY AFTER RECOVERY ===")
            time.sleep(3)  # Wait a bit for changes to take effect
            connectivity_ok = test_connectivity('services.sanremomachines.com')
            
            if connectivity_ok:
                print("✅ Connectivity restored!")
            else:
                print("❌ Connectivity still broken. A system restart may be required.")
        else:
            print("Skipping recovery attempt.")
    else:
        print(f"\n✅ Connectivity to services.sanremomachines.com appears to be working.")
        print("You can now try running the fixed API client.")


if __name__ == "__main__":
    main()
