# Bootly - Android Image Workstation 🚀

Bootly is a modern, professional toolkit for managing, unpacking, and repacking Android boot and recovery images. It features a high-fidelity glassmorphism GUI, smart workspace exploration, and a suite of developer-focused tools built on PyQt6.

![Bootly Mockup](https://github.com/Haris16-code/Bootly/blob/main/data/bootly_gui_mockup_1774961494950.png)

## ✨ Features
- **High-Fidelity GUI**: Modern PyQt6 interface with a professional dark mode and fluid animations.
- **Smart Workspace**: Manage raw images and unpacked projects in a fluid grid-based explorer.
- **Visual Metadata Parser**: Real-time extraction and visualization of image structures (Kernel, Ramdisk, OS version, Header).
- **Auto-Updater**: Built-in engine for both standalone binary (.exe) and source code updates.
- **Responsive Knowledge Base**: Searchable manual with real-time keyword highlighting.
- **Email Updates**: Direct subscription to software updates via a native, secure form.
- **Privacy-First Analytics**: Anonymous usage and error telemetry via GA4 (no sensitive data collected).

## 🛠️ Prerequisites
- **Python 3.10+** (if running from source)
- **Pip** (Python package manager)
- **Binaries**: The `bin/` folder must contain the necessary Android image tools (`mkbootimg`, `unpackbootimg`, etc.).

---

## 🚀 Running Guide

### ⊞ Windows (Recommended)
1. **From Standalone EXE**:
   - Download the latest `Bootly.exe` from the [Releases](https://github.com/Haris16-code/Bootly/releases) page.
   - Simply run the EXE. (Make sure the `bin/` folder is in the same directory).
2. **From Source**:
   - Open your terminal (PowerShell or CMD) in the project root.
   - Install dependencies: `pip install -r requirements.txt`
   - Launch: `python main.py`

### 🐧 Linux
*Note: Bootly's core logic is cross-platform, but the image processing tools in `/bin` are currently Windows-based. Linux users will need to replace the files in `/bin` with Linux-compatible binaries.*
1. Install system dependencies:
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-pyqt6
   ```
2. Open terminal in project root and install requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Launch:
   ```bash
   python3 main.py
   ```

### 🍎 macOS
*Note: MacOS users will need to provide native image processing tools in the `/bin` directory and install the following dependencies.*
1. Open Terminal in project root.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Launch:
   ```bash
   python3 main.py
   ```

---

## 📁 Project Structure
- `main.py`: Primary application entry point and GUI logic.
- `core/`:
  - `image_manager.py`: Controls image manipulation and process handling.
  - `updater.py`: Background update engine and version checking.
  - `analytics.py`: Telemetry and usage tracking dispatcher.
  - `utils.py`: General utility functions.
- `bin/`: Contains the binary tools for Android image manipulation.
- `input/`: Recommended directory for raw images.
- `output/`: Default directory for repacked images.

---

## 🤝 Contributing
Bootly is an open-source project. We welcome contributions, bug reports, and suggestions!

## 📄 Credits
- **Developed by**: Haris
- **Legacy Logic**: Inspired by the functionality of Carliv Image Kitchen.

---
*Developed with ❤️ for the Android Community.*
