#!/usr/bin/env python3
"""
Download TrailBase binary for the current platform.
"""
import json
import os
import platform
import subprocess
import sys
import zipfile
from pathlib import Path


def get_platform_info():
    """Get platform information for TrailBase download."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == "darwin":
        if machine in ["x86_64", "amd64"]:
            return "x86_64_apple_darwin"
        elif machine in ["arm64", "aarch64"]:
            return "arm64_apple_darwin"
    elif system == "linux":
        if machine in ["x86_64", "amd64"]:
            return "x86_64_linux"
    elif system == "windows":
        if machine in ["x86_64", "amd64"]:
            return "x86_64_windows"
    
    raise ValueError(f"Unsupported platform: {system} {machine}")


def download_trailbase():
    """Download TrailBase binary."""
    try:
        platform_suffix = get_platform_info()
        print(f"Detected platform: {platform_suffix}")
        
        # For now, use a known version since GitHub API might be rate-limited
        version = "v0.14.1"  # You can update this to the latest version
        print(f"Using TrailBase version: {version}")
        
        # Download URL
        download_url = f"https://github.com/trailbaseio/trailbase/releases/download/{version}/trailbase_{version}_{platform_suffix}.zip"
        zip_filename = f"trailbase_{version}_{platform_suffix}.zip"

        print(f"Downloading TrailBase from: {download_url}")
        
        # Download the ZIP file
        result = subprocess.run([
            "curl", "-L", "-o", zip_filename, download_url
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Download failed: {result.stderr}")
            print("\nManual download instructions:")
            print("1. Visit: https://trailbase.io/")
            print("2. Download the binary for your platform")
            print("4. Make it executable: chmod +x trailbase")
            return
        
        print(f"Downloaded {zip_filename}, extracting...")
        
        # Extract the ZIP file
        with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
            zip_ref.extractall('.')
        
        # Find the binary file (it might be named differently inside the ZIP)
        binary_name = None
        for file in os.listdir('.'):
            if file.startswith('trail') and not file.endswith('.zip'):
                binary_name = file
                break
        
        if not binary_name:
            print("Could not find trailbase binary in the extracted files")
            print("Available files:", os.listdir('.'))
            return
        
        # Rename to 'trailbase'
        # if binary_name != 'trailbase':
        #     os.rename(binary_name, 'trailbase')
        
        # Make it executable
        os.chmod("trail", 0o755)
        
        # Clean up the ZIP file
        os.remove(zip_filename)
        
        print("TrailBase downloaded and extracted successfully!")
        print("You can now run: make trailbase-start")
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nManual download instructions:")
        print("1. Visit: https://trailbase.io/")
        print("2. Download the binary for your platform")
        print("4. Make it executable: chmod +x trail")


if __name__ == "__main__":
    download_trailbase() 