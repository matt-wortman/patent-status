# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

Patent Status Tracker is a standalone Windows application for monitoring USPTO patent application status changes. It provides a GUI for tracking multiple patent applications and viewing recent updates.

## Tech Stack

- **Python 3.10+** - Core language
- **CustomTkinter** - Modern GUI framework
- **SQLite** - Local database storage
- **keyring** - Windows Credential Manager for secure API key storage
- **PyInstaller** - Creates standalone .exe

## Commands

```bash
# Development
python main.py                    # Run the application

# Build
python build.py                   # Build standalone .exe
pyinstaller PatentStatusTracker.spec  # Alternative build method

# Dependencies
pip install -r requirements.txt   # Install dependencies
```

## Project Structure

```
patent-status-tracker/
├── main.py                       # Entry point
├── src/
│   ├── ui.py                     # CustomTkinter GUI (main window, tabs)
│   ├── database.py               # SQLite operations for patents/events/settings
│   ├── credentials.py            # Windows Credential Manager integration
│   ├── uspto_api.py              # USPTO API client
│   └── polling.py                # Background polling service
├── build.py                      # PyInstaller build script
├── PatentStatusTracker.spec      # PyInstaller spec file
├── requirements.txt              # Python dependencies
└── IMPROVEMENT_PLAN.md           # Current UI improvement plan
```

## Key Files

- **`src/database.py`** - SQLite database with tables for patents, events, settings
- **`src/ui.py`** - Main UI with three tabs: Updates, All Patents, Settings
- **`src/credentials.py`** - Secure API key storage via Windows Credential Manager
- **`src/uspto_api.py`** - USPTO Open Data Portal API integration

## Data Storage

- **Database**: `Documents/PatentStatusTracker/patents.db`
- **API Key**: Windows Credential Manager (secure, not in files)

## USPTO API

- Base URL: `https://api.uspto.gov/api/v1/patent/applications/{appNum}`
- Authentication: `X-API-Key` header
- No webhooks available - polling required

## Plan Files

When creating plans for this project:
- Write plan files to THIS directory (e.g., `IMPROVEMENT_PLAN.md`)
- Do NOT write to `~/.claude/plans/`
- Write the plan file BEFORE presenting it to the user
