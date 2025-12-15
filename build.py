#!/usr/bin/env python3
"""
Build script for creating the Windows executable.

Run this script on Windows to create a standalone .exe file.
"""

import PyInstaller.__main__
import os
import shutil

# Get the directory of this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Output directory
DIST_DIR = os.path.join(BASE_DIR, "dist")
BUILD_DIR = os.path.join(BASE_DIR, "build")

# Clean previous builds
for dir_path in [DIST_DIR, BUILD_DIR]:
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)

# PyInstaller arguments
args = [
    os.path.join(BASE_DIR, "main.py"),
    "--name=PatentStatusTracker",
    "--onefile",  # Single executable
    "--windowed",  # No console window
    "--clean",
    f"--distpath={DIST_DIR}",
    f"--workpath={BUILD_DIR}",
    # Include all source files
    f"--add-data={os.path.join(BASE_DIR, 'src')}:src",
    # Hidden imports that PyInstaller might miss
    "--hidden-import=keyring.backends.Windows",
    "--hidden-import=customtkinter",
    "--hidden-import=tksheet",
    "--hidden-import=PIL",
    "--hidden-import=PIL._tkinter_finder",
]

# Run PyInstaller
print("Building Patent Status Tracker...")
print("-" * 50)
PyInstaller.__main__.run(args)

print("-" * 50)
print(f"Build complete! Executable is at:")
print(f"  {os.path.join(DIST_DIR, 'PatentStatusTracker.exe')}")
print()
print("You can distribute this single .exe file to users.")
print("No installation or admin privileges required.")
