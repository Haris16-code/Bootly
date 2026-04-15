# Bootly - Android Image Workstation 🚀

Bootly is a modern, professional toolkit for managing, unpacking, and repacking Android boot and recovery images. It features a high-fidelity glassmorphism GUI, smart workspace exploration, and a suite of developer-focused tools built on PyQt6.

![Bootly Mockup](https://github.com/Haris16-code/Bootly/blob/main/data/bootly-mockup.PNG?raw=true)

## ✨ Features
- **Unpack & Repack Boot Image**: Seamlessly single-click extract and rebuild Android boot/recovery images into clean directories.
- **Root Your Phone (Experimental)**: High-performance one-click automatic rooting suite and manual patching for local `boot.img` files.
- **Patch Boot Image**: Integrated Magisk-based patching workflow for effortless rooting.
- **DAT to IMG Builder**: Rapidly convert sparse Android DAT images into raw system images.
- **AVB Master Tool Suite**: Full GUI integration of `avbtool.py` for standalone VBMeta generation, hash footer appending, custom cryptographic signing (RSA), and partition verification.
- **High-Fidelity GUI**: Modern PyQt6 interface with a premium dark mode, glassmorphism aesthetics, and fluid responsive toolcards.
- **Smart Workspace**: Manage raw images and unpacked projects in a fluid grid-based explorer complete with intelligent conflict resolution.
- **Visual Metadata Parser**: Real-time extraction and visualization of deep image structures (Kernel, Ramdisk, OS version, Header).
- **Responsive Knowledge Base**: Searchable manual with premium typography and real-time keyword highlighting.
## 🛠️ Prerequisites
- **Python 3.10+** (if running from source)
- **Pip** (Python package manager)
- **Binaries**: The `bin/` folder must contain the necessary Android image tools (`mkbootimg`, `unpackbootimg`, etc.).

---

## 🚀 Running Guide

### 🪟 Windows (Recommended)
1. **From Standalone EXE**:
   - Download the latest `Bootly.exe` from the [Releases](https://github.com/Haris16-code/Bootly/releases) page.
   - Simply run the EXE. (Make sure the `bin/` folder is in the same directory).
2. **From Source**:
   - Open your terminal (PowerShell or CMD) in the project root.
   - Install dependencies: `pip install -r requirements.txt`
   - Launch: `python main.py`

### 🐧 Linux
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

## 📚 Developer Documentation
For technical insights into Bootly's core architecture, UI logic, and offline execution engine, check out the [Bootly Developers Guide](Documentation/Developers_Guide.md).

---

## Bootly Community

Join the development community, share feedback, and collaborate with other Android modding developers:

**Join Community:** https://bootly.harislab.tech

---

## 🤝 Contributing
Bootly is an open-source project. We welcome contributions, bug reports, and suggestions!
**GitHub Repository**: [https://github.com/Haris16-code/Bootly](https://github.com/Haris16-code/Bootly)

## 📄 Credits
- **Developed by**: Haris
- **Legacy Logic**: Inspired by the functionality of Carliv Image Kitchen.

---
*Developed with ❤️ for the Android Community.*
