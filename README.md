# VDesk Manager

A lightweight Windows desktop environment manager. Manage and switch virtual desktops from your system tray with keyboard shortcuts and a clean menu interface.

[![GitHub release (latest by date)](https://img.shields.io/github/v/release/hoiwanchang/VDeskManager)](https://github.com/hoiwanchang/VDeskManager/releases/latest)
[![Build Status](https://img.shields.io/github/actions/workflow/status/hoiwanchang/VDeskManager/release.yml?branch=master&label=build)](https://github.com/hoiwanchang/VDeskManager/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## Features

- **🖥️ System Tray Icon** — Live grid overview showing your current desktop number and total desktop count
- **⚡ Quick Switch** — Right-click menu to jump to any desktop instantly
- **➕ Create Desktops** — Add new virtual desktops with one click
- **✕ Remove Desktops** — Delete unwanted desktops
- **✎ Rename Desktops** — Give your desktops meaningful names
- **⇄ Move Window** — Move the foreground window to any desktop
- **⌨️ Global Hotkeys** — `Ctrl+Alt+←/→` to switch, `Ctrl+Alt+1-9` to jump to a specific desktop
- **🔍 Search Desktops** — Filter desktops by name or number (useful with many desktops)
- **🎬 Toggle Animations** — Control Windows desktop transition animations
- **🖥️ Multi-Monitor** — Switch desktops on all monitors in sync or independently per monitor
- **♻️ Auto-Reload Hotkeys** — Modify `hotkeys.json` and see changes apply immediately
- **⚙️ Config Export/Import** — Backup and restore all settings to a single JSON file
- **🔀 Window Auto-Route** — Automatically move windows to specific desktops based on class/title rules
- **📦 Desktop Sets** — Define groups of desktops (e.g. "Work", "Dev") with custom names
- **📦 Single EXE** — PyInstaller-built standalone executable, no Python required

## System Requirements

- Windows 10 (1903 / Build 18362+) or Windows 11
- x64 architecture

## Quick Start

### Option 1: Download Release (Recommended)

1. Download the latest `.exe` from the [Releases page](https://github.com/hoiwanchang/VDeskManager/releases)
2. Double-click `VDeskManager.exe` — the tray icon appears in the taskbar

### Option 2: Run from Source

```batch
:: Install dependencies
pip install -r requirements.txt

:: Launch
python main.py
```

Or double-click `start.bat`.

### Option 3: Build from Source

```batch
pip install pyinstaller
build.bat
```

Outputs `dist/VDeskManager.exe`.

## Usage

After launching, a tray icon appears in the system tray:

| Action | Result |
|--------|--------|
| **Left-click** | Open the desktop switch menu |
| **Right-click** | Open the full feature menu |
| **Scroll** | Switch to the previous/next desktop |

### Keyboard Shortcuts (Default)

| Hotkey | Action |
|--------|--------|
| `Ctrl+Alt+←` | Previous desktop |
| `Ctrl+Alt+→` | Next desktop |
| `Ctrl+Alt+1` – `Ctrl+Alt+9` | Jump to desktop 1-9 |

Customize hotkeys in `~/.vdesk-manager/hotkeys.json` (edit → the app auto-reloads).

### Tray Icon Modes

The icon adapts to your desktop count:

| Desktops | Display |
|----------|---------|
| 1–4 | 2×2 grid with active desktop highlighted in blue |
| 5–9 | 3×3 grid with active desktop highlighted in blue |
| 10+ | Current desktop number |

### CLI Quick Commands

```batch
python main.py --switch 3                  :: Switch to desktop 3, then exit
python main.py --switch-dir 1              :: Move to the next desktop, then exit
python main.py --create                    :: Create a new desktop, then exit
python main.py --delete 2                  :: Delete desktop 2, then exit
python main.py --move-window 4             :: Move foreground window to desktop 4, then exit
python main.py --rename 1 "Work"           :: Rename desktop 1 to "Work", then exit
python main.py --log-level DEBUG           :: Enable debug logging
python main.py --no-hotkeys                :: Run without global hotkeys
```

### Multi-Monitor Switching

Go to **⚙ Config → Multi-Monitor** to choose:

- **Sync** — All monitors switch to the same desktop together (default)
- **Independent** — Each monitor maintains its own set of virtual desktops

Requires Windows 11.

### Window Auto-Route

Define rules to automatically move windows to specific desktops. Edit `~/.vdesk-manager/win_autoroute.json`:

```json
{
  "rules": [
    {
      "target_desktop": 1,
      "name_contains": "Chrome",
      "class_name": ""
    },
    {
      "target_desktop": 2,
      "name_contains": "VS Code",
      "class_name": ""
    }
  ]
}
```

Rules are matched in order. Empty `class_name` or `name_contains` means that filter is ignored.

## Project Structure

```
VDeskManager/
├── main.py                    # Entry point
├── start.bat                  # Windows launcher
├── build.bat                  # PyInstaller build script
├── requirements.txt           # Python dependencies
├── VDeskManager.spec          # PyInstaller spec file
├── CHANGELOG.md               # Version history
├── pyproject.toml             # Project config + pytest settings
├── assets/                    # Icons and images
│   └── vdesk_manager_icon.png # Application icon
├── src/
│   ├── __init__.py
│   ├── version.py             # Version info
│   ├── desktop_manager.py     # Core virtual desktop management
│   ├── tray_icon.py           # System tray indicator & menu
│   ├── icon_generator.py      # Dynamic icon rendering (Pillow)
│   ├── hotkey_manager.py      # Global hotkey registration
│   ├── autostart.py           # Boot via Windows Task Scheduler
│   ├── name_manager.py        # Desktop ID-to-name mapping
│   ├── desktop_sets.py        # Desktop group definitions
│   ├── win_autoroute.py       # Window auto-routing rules
│   ├── config_export.py       # Config backup/restore
│   ├── monitor_manager.py     # Multi-monitor enumeration
│   └── switch_animation.py    # Animation toggle via registry
└── tests/                     # Unit tests
    ├── conftest.py
    ├── test_version.py
    ├── test_icon_generator.py
    ├── test_hotkey_manager.py
    └── test_switch_animation.py
```

## Configuration

All settings are stored in `~/.vdesk-manager/`:

| File | Purpose |
|------|---------|
| `hotkeys.json` | Keyboard shortcut definitions |
| `desktop_names.json` | Desktop ID → name mappings (persists through reordering) |
| `desktop_sets.json` | Desktop group definitions |
| `win_autoroute.json` | Window auto-routing rules |
| `logs/vdesk.log` | Application log (rotating, 5MB × 5 backups) |

## Build & Release

This project uses GitHub Actions to build releases automatically.

1. Push a git tag `v*`:
   ```bash
   git tag -a v1.3.0 -m "v1.3.0 - feature description"
   git push origin v1.3.0
   ```
2. The `release.yml` workflow builds a single-file EXE via PyInstaller
3. An asset `VDeskManager.exe` is uploaded to the GitHub Release

## Dependencies

| Package | Purpose |
|---------|---------|
| [pyvda](https://github.com/mirober/pyvda) | Windows Virtual Desktop COM API wrapper |
| [pystray](https://github.com/moses-palmer/pystray) | Cross-platform system tray icon |
| [Pillow](https://python-pillow.org/) | Image rendering for tray icons |
| [pynput](https://github.com/moses-palmer/pynput) | Global keyboard hooks |

## Known Limitations

- Virtual desktop APIs use undocumented Windows COM interfaces; occasional Windows updates may temporarily break functionality
- Per-monitor virtual desktops require Windows 11
- Global hotkeys may conflict with system or third-party software (use the conflict detector or `--no-hotkeys`)

## License

MIT License
