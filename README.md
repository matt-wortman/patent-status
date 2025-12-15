# Patent Status Tracker

A standalone Windows application for monitoring USPTO patent application status changes.

## Features

- **Track Multiple Patents**: Add any US patent application by number
- **Automatic Updates**: Polls USPTO at configurable intervals (1-168 hours)
- **Change Detection**: See what's new in the last 1-90 days
- **USPTO Links**: Quick access to Patent Center and Public PAIR
- **Secure Storage**: API key stored in Windows Credential Manager (not in files)
- **No Installation**: Single .exe file, no admin rights needed
- **Export**: CSV export for reporting

## Quick Start

### For End Users

1. Download `PatentStatusTracker.exe`
2. Double-click to run (no installation needed)
3. Go to **Settings** tab
4. Enter your USPTO API key (get one free at https://data.uspto.gov/apis/getting-started)
5. Go to **All Patents** tab
6. Add patent application numbers to track

### Getting a USPTO API Key

1. Go to https://data.uspto.gov/apis/getting-started
2. Click "MyODP" to create an account
3. You'll need a MyUSPTO account (free)
4. Once logged in, generate your API key
5. Copy the key into the Settings tab of this app

## Screenshots

```
┌─────────────────────────────────────────────────────────────────┐
│  Patent Status Tracker                               [─] [□] [×]│
├────────────────┬────────────────┬───────────────────────────────┤
│ [Updates]      │ [All Patents]  │ [Settings]                    │
├─────────────────────────────────────────────────────────────────┤
│  Show updates from last: [7 days ▼]              [Refresh Now]  │
├─────────────────────────────────────────────────────────────────┤
│ Date       │ App #       │ Event     │ Description              │
│────────────│─────────────│───────────│──────────────────────────│
│ 2025-12-08 │ 17/940,142  │ BRCE      │ RCE - Begin              │
│ 2025-09-30 │ 18/413,823  │ NOA       │ Notice of Allowance      │
│ 2025-06-16 │ 18/635,578  │ MCTNF     │ Mail Non-Final Rejection │
└─────────────────────────────────────────────────────────────────┘
                          Last checked: 2025-12-15 10:30
```

## Building from Source

### Requirements

- Python 3.10+
- Windows (for PyInstaller to create Windows executable)

### Setup

```bash
# Clone or download the source
cd patent-status-tracker

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run in Development

```bash
python main.py
```

### Build Executable

```bash
python build.py
```

The executable will be created at `dist/PatentStatusTracker.exe`

## Data Storage

- **Database**: `Documents/PatentStatusTracker/patents.db` (SQLite)
- **API Key**: Windows Credential Manager (secure)
- **Settings**: Stored in the SQLite database

## Troubleshooting

### "Invalid API Key" error
- Verify your key at https://data.uspto.gov/swagger/index.html
- Keys may expire - generate a new one if needed

### "Application not found" error
- Verify the application number is correct
- Numbers should be 8 digits (e.g., 17940142 or 17/940,142)
- Only published applications are available via API

### App won't start
- Ensure you have Windows 10 or later
- Try running as administrator once to initialize

## License

MIT License - feel free to modify and distribute.

## Support

For USPTO API issues: https://data.uspto.gov/support
For app issues: Contact your IT department
