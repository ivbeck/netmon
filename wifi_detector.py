#!/usr/bin/env python3
"""
WiFi Network Detection Utilities

This module provides functions to detect the current WiFi network name
and organize data by network.
"""

import subprocess
import re
import sys
from pathlib import Path


def get_wifi_network_name():
    """
    Get the current WiFi network name (SSID)
    Returns a sanitized network name or 'unknown' if detection fails
    """
    try:
        # Try different methods based on the OS
        if sys.platform.startswith("linux"):
            return _get_wifi_linux()
        elif sys.platform == "darwin":  # macOS
            return _get_wifi_macos()
        elif sys.platform.startswith("win"):
            return _get_wifi_windows()
        else:
            return "unknown"
    except Exception as e:
        print(f"Error detecting WiFi network: {e}")
        return "unknown"


def _get_wifi_linux():
    """Get WiFi network name on Linux"""
    try:
        # Try nmcli first (NetworkManager)
        result = subprocess.run(
            ["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if line.startswith("yes:"):
                    ssid = line.split(":", 1)[1]
                    return sanitize_network_name(ssid)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    try:
        # Try iwgetid as fallback
        result = subprocess.run(
            ["iwgetid", "-r"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return sanitize_network_name(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    try:
        # Try parsing /proc/net/wireless and iwconfig
        result = subprocess.run(["iwconfig"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            # Look for ESSID in iwconfig output
            match = re.search(r'ESSID:"([^"]*)"', result.stdout)
            if match:
                essid = match.group(1)
                if essid and essid != "off/any":
                    return sanitize_network_name(essid)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return "unknown"


def _get_wifi_macos():
    """Get WiFi network name on macOS"""
    try:
        result = subprocess.run(
            [
                "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport",
                "-I",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if "SSID:" in line:
                    ssid = line.split("SSID:")[1].strip()
                    return sanitize_network_name(ssid)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    try:
        # Alternative method using networksetup
        result = subprocess.run(
            ["networksetup", "-getairportnetwork", "en0"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            if "Current Wi-Fi Network:" in output:
                ssid = output.split("Current Wi-Fi Network:")[1].strip()
                return sanitize_network_name(ssid)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return "unknown"


def _get_wifi_windows():
    """Get WiFi network name on Windows"""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "profiles"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            # This is a simplified approach - in practice, you'd want to
            # get the currently connected profile
            for line in result.stdout.split("\n"):
                if "All User Profile" in line:
                    match = re.search(r": (.+)$", line)
                    if match:
                        return sanitize_network_name(match.group(1).strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return "unknown"


def sanitize_network_name(name):
    """
    Sanitize network name for use in file paths
    Remove or replace characters that are not filesystem-safe
    """
    if not name or name.lower() in ["unknown", "off/any", ""]:
        return "unknown"

    # Replace problematic characters with underscores
    sanitized = re.sub(r'[<>:"/\\|?*\s]', "_", name)
    sanitized = re.sub(r"[^\w\-_.]", "_", sanitized)
    sanitized = re.sub(
        r"_+", "_", sanitized
    )  # Replace multiple underscores with single
    sanitized = sanitized.strip("_")  # Remove leading/trailing underscores

    # Limit length to 50 characters
    if len(sanitized) > 50:
        sanitized = sanitized[:50]

    return sanitized or "unknown"


def get_current_network_info():
    """
    Get comprehensive network information
    Returns a dict with network name and additional info
    """
    network_name = get_wifi_network_name()

    return {
        "name": network_name,
        "sanitized_name": sanitize_network_name(network_name),
        "timestamp": None,  # Will be set when used
    }


if __name__ == "__main__":
    # Test the WiFi detection
    network = get_wifi_network_name()
    print(f"Current WiFi Network: {network}")
    print(f"Sanitized: {sanitize_network_name(network)}")
