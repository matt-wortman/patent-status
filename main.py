#!/usr/bin/env python3
"""Patent Status Tracker - Main entry point.

A standalone Windows application for monitoring USPTO patent application status
changes. Provides a modern GUI for tracking multiple patent applications with
automatic background polling for updates.

Features:
    - Track multiple patent applications simultaneously
    - Automatic background polling for status updates
    - Secure API key storage in Windows Credential Manager
    - Export patent data to CSV
    - Direct links to Patent Center and Public PAIR
    - Hierarchical event view with filtering
    - Customizable table columns and display settings

Usage:
    python main.py              # Run in development mode
    PatentStatusTracker.exe     # Run as compiled executable

Requirements:
    - Python 3.10+ (for development)
    - USPTO Open Data Portal API key (free registration required)
    - Windows OS (for Credential Manager integration)
"""

import sys
import os

# Ensure the src directory is in the path
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    app_dir = os.path.dirname(sys.executable)
else:
    # Running as script
    app_dir = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, app_dir)

from src.ui import run_app


def main():
    """Main entry point for the application.

    Initializes and runs the Patent Status Tracker GUI. Handles any fatal
    errors by displaying an error dialog to the user.
    """
    try:
        run_app()
    except Exception as e:
        import traceback
        error_msg = f"Fatal error: {str(e)}\n\n{traceback.format_exc()}"

        # Try to show error dialog
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Patent Status Tracker - Error", error_msg)
            root.destroy()
        except:
            print(error_msg)

        sys.exit(1)


if __name__ == "__main__":
    main()
