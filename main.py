#!/usr/bin/env python3
"""
Patent Status Tracker - Main entry point.

A standalone Windows application for monitoring USPTO patent application status.
No installation required - just run the executable.

Features:
- Track multiple patent applications
- Automatic polling for status updates
- Secure API key storage in Windows Credential Manager
- Export to CSV
- Links to Patent Center and Public PAIR
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
    """Main entry point."""
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
