#!/usr/bin/env python3
"""
Script to check which Modbus TCP ports are open on a specific host.
"""

import socket
import sys

def check_port(host, port, timeout=2):
    """
    Check if a port is open on the given host.
    
    Args:
        host: IP address or hostname
        port: Port number to check
        timeout: Timeout in seconds (default: 2)
    
    Returns:
        True if port is open, False otherwise
    """
    try:
        socket.setdefaulttimeout(timeout)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"  Error checking port {port}: {e}")
        return False

def main():
    host = "192.168.0.113"
    ports = [502, 503, 5020, 5502, 1502, 8502]
    timeout = 2
    
    print(f"Checking Modbus TCP ports on {host} (timeout: {timeout}s)\n")
    print("=" * 50)
    
    open_ports = []
    closed_ports = []
    
    for port in ports:
        is_open = check_port(host, port, timeout)
        status = "OPEN" if is_open else "CLOSED"
        print(f"Port {port:5d}: {status}")
        
        if is_open:
            open_ports.append(port)
        else:
            closed_ports.append(port)
    
    print("=" * 50)
    print(f"\nSummary:")
    print(f"  Open ports:   {open_ports if open_ports else 'None'}")
    print(f"  Closed ports: {closed_ports if closed_ports else 'None'}")

if __name__ == "__main__":
    main()
