# Bootly Developer & Source Code Guide

Welcome to the internal source code documentation for **Bootly**. This guide breaks down the architectural modules, class diagrams, and cross-platform logic designed to make Android Boot/Recovery image handling seamless locally on a desktop environment.

---

## 1. Directory Architecture

```text
Bootly-Dev/
│
├── main.py                   # Primary Entry Point & PyQt6 GUI Application
├── requirements.txt          # Python Package Dependencies
├── README.md                 # Public-facing Documentation
│
├── core/                     # Internal Logic Engine
│   ├── image_manager.py      # Binary Execution & AVB Cryptography
│   └── utils.py              # Cross-Platform Handlers & Workspace Cleaners
│
├── bin/                      # Platform-specific binaries
│   ├── scripts/              # AOSP Python Scripts (e.g., avbtool.py)
│   ├── mkbootimg.exe         # Windows Binaries for repacking
│   └── unpackbootimg.exe     # Windows Binaries for unpacking
│
├── Documentation/            # Developer and architecture documents
├── input/                    # Raw images dropped by User
└── output/                   # Processed/Repacked target images
```

---

## 2. Core Modules Breakdown

### 2.1 `main.py` (The GUI Manager)
Bootly leverages `PyQt6` for a scalable "Glassmorphism" / "Sleek Dark" interface. 
- **`BootlyApp` (QMainWindow)**: The core state machine of the app. It manages a `QStackedWidget` to seamlessly transition between virtual pages:
  1. **Dashboard**: Image selection, live metadata viewing, and primary processing (Unpack/Repack).
  2. **Workspace Explorer**: Grid-based layout checking the localized `input/` and `output/` folders to manage projects.
  3. **AVB Master Tool**: Dedicated suite for generating custom VBMeta images, applying RSA signatures, and verifying integrity.
  4. **Knowledge Base**: Internal lookup database viewer.
- **`WorkerThread` (QThread)**: PyQt GUI applications lock up strictly if heavy operations block the main thread. We utilize `WorkerThread` to run IO tasks (like heavy image unpacking/repacking) entirely in the background, continuously emitting `log_signal` and `finished` events back to the synchronous UI console.

### 2.2 `core/image_manager.py` (The Execution Engine)
Responsible for directly interacting with `.img` files and spawning subprocesses to utilize internal `bin/` tools.
- **`unpack()`**: Dissects an Android image format (identifying QCOM or Mediatek headers), uses `unpackbootimg`, and intercepts STDOUT streams for live-console rendering.
- **`repack()`**: Analyzes modified workspace directories, securely packages a new ramdisk and kernel utilizing `mkbootimg`, and applies custom image descriptors.
- **God-Tier Security Bypass**: In `repack()`, custom regex logic (`_patch_security_flags`) scans the local `fstab` and active `vbmeta.img` files to forcefully strip `dm-verity` and `avb` verification flags directly from the ramdisk.
- **AVB Wrappers**: Higher order wrappers (`avb_verify_image`, `avb_add_hash_footer`, `generate_empty_vbmeta`) dynamically pass custom command line arguments to the localized `bin/scripts/avbtool.py`. Uses python's `os.urandom()` to pass cryptographic salts, avoiding dependency on missing OS-specific randomizer nodes.

### 2.3 `core/utils.py` (Path Resolution)
Because Bootly acts as a generalized tool, finding exact dependencies dynamically on the local machine is critical.
- **`get_bin_path()`**: Maps binary executions properly. On Windows, it automatically searches and appends `.exe`.
- **`get_os()`**: Recognizes Linux vs macOS vs Windows to properly map internal OS execution chains without relying on external paths.
- **Directory Managers**: Exposes `ensure_dir()` and `clear_dir()` functions to securely route unzipped ramdisk folders and wipe isolated tool caches automatically.

---

## 4. Operational Workflows

### How Bootly Builds & Patches AVB:
1. User drops `boot.img` -> Clicks "Repack" + "Patch VBMeta".
2. `BootlyApp` spawns `WorkerThread(ImageManager.repack)`.
3. `ImageManager` recompresses the active local ramdisk.
4. Spawns system python targeting the internal `/bin/scripts/avbtool.py` script.
5. Issues command: `patch_vbmeta --flags 2` directly onto the local output files to forcibly override verification bits.
6. Passes STDOUT cleanly to PyQt UI via Thread Signal Slots. Emits final `[SUCCESS]` directly to the user dashboard.

### Memory & Workspace Cleanliness
It is strictly enforced that `input/`, `output/`, and active unpacked working directories inside `Bootly-Dev` are wiped via `clear_dir()` on explicit app-closing mechanisms, ensuring the desktop app never balloons on the user's hard drive space uncontrollably tracking heavy image formats.

---
*Developed for Android Image Manipulation and Security Bypass Configuration.*
