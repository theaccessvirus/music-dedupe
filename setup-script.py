#!/usr/bin/env python3
"""
Setup script for Music Dedupe GUI application
This will create an executable with PyInstaller
"""

import os
import sys
import platform
import subprocess

# Define app information
APP_NAME = "MusicDedupe"
VERSION = "1.0.0"
DESCRIPTION = "Find and manage duplicate music files"

# Required packages
REQUIRES = [
    "tkinterdnd2",
    "mutagen",
    "pyinstaller"
]

def install_dependencies():
    """Install required dependencies"""
    print("Installing required dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade"] + REQUIRES)
        print("All dependencies installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        sys.exit(1)

def create_icon():
    """Create a simple icon for the application"""
    try:
        from PIL import Image, ImageDraw
        
        # Create a 128x128 px image
        size = (128, 128)
        img = Image.new('RGBA', size, color=(255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw a music note shape
        # Main circle
        draw.ellipse((20, 60, 60, 100), fill=(41, 128, 185))
        # Stem
        draw.rectangle((55, 30, 65, 80), fill=(41, 128, 185))
        # Flag
        points = [(65, 30), (95, 20), (85, 50), (65, 45)]
        draw.polygon(points, fill=(41, 128, 185))
        
        # Draw a smaller duplicate music note
        # Main circle
        draw.ellipse((60, 80, 90, 110), fill=(231, 76, 60, 180))
        # Stem
        draw.rectangle((85, 50, 95, 90), fill=(231, 76, 60, 180))
        # Flag
        points = [(95, 50), (115, 40), (105, 65), (95, 60)]
        draw.polygon(points, fill=(231, 76, 60, 180))
        
        # Save as ico
        img.save('music_dedupe.ico')
        print("Created icon: music_dedupe.ico")
        
        # For macOS, create an icns file
        if sys.platform == 'darwin':
            try:
                # Create a PNG with transparency
                img.save('music_dedupe.png')
                print("Created icon: music_dedupe.png")
            except:
                print("Could not create PNG icon (will use default icon)")
    except ImportError:
        print("Pillow (PIL) not installed. Using default icon.")
        # Just create an empty file as a placeholder
        with open('music_dedupe.ico', 'wb') as f:
            f.write(b'')

def create_executable():
    """Create executable using PyInstaller"""
    print("Creating executable with PyInstaller...")
    
    # Create a simple icon
    create_icon()
    
    # Build the executable
    pyinstaller_args = [
        "pyinstaller",
        "--name=MusicDedupe",
        "--onefile",
        "--windowed",
        "--icon=music_dedupe.ico",
        "--add-data=music_dedupe.ico:."
    ]
    
    # Add platform-specific options
    if sys.platform == 'darwin':
        print("Building for macOS...")
        pyinstaller_args.append('--osx-bundle-identifier=com.musicdedupe.app')
        
        # Check if running on Apple Silicon
        if platform.machine() == 'arm64':
            print("Building for Apple Silicon (ARM64)...")
            pyinstaller_args.append('--target-architecture=arm64')
    
    # Add the script to build
    pyinstaller_args.append("music_dedupe_gui.py")
    
    try:
        subprocess.check_call(pyinstaller_args)
        print("\nExecutable created successfully in the 'dist' directory!")
        
        # Print the full path to the executable
        if sys.platform == 'darwin':
            exe_path = os.path.abspath(os.path.join('dist', 'MusicDedupe.app'))
        else:
            exe_path = os.path.abspath(os.path.join('dist', 'MusicDedupe.exe' if sys.platform == 'win32' else 'MusicDedupe'))
        
        print(f"\nExecutable path: {exe_path}")
        
        # Fix macOS app permissions
        if sys.platform == 'darwin':
            print("\nSetting macOS app permissions...")
            try:
                subprocess.check_call(["chmod", "-R", "+x", exe_path])
                print("Permissions set successfully.")
            except Exception as e:
                print(f"Warning: Could not set permissions: {e}")
        
        print("\nYou can now run this executable without needing Python installed.")
    except subprocess.CalledProcessError as e:
        print(f"Error creating executable: {e}")
        sys.exit(1)

def main():
    print(f"Setting up {APP_NAME} v{VERSION}...")
    print(f"Platform: {sys.platform}, Architecture: {platform.machine()}")
    
    # Install required packages
    install_dependencies()
    
    # Create the executable
    create_executable()
    
    print("\nSetup completed successfully!")

if __name__ == "__main__":
    main()