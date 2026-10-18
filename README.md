# Flash npmBuilder v1.02 – Initial Release

**Flash npmBuilder** is a zero-config, portable Windows GUI application built to help creators, prompt engineers, and non-technical users build, preview, and run React, Vite, and Next.js web projects locally—without needing Visual Studio Code, command lines, or manual npm installations.

---

### 👤 Credits & Authorship
- **Conceived & Created by:** Mr. Saqlain
- **Developed by:** **Tech Realtime** & **SaQuiz Perks**
- **YouTube Channel:** [Tech Realtime](https://www.youtube.com/@TechRealtime)

---

## ✨ Key Features

- **Streamlined Tabbed Interface**:
  - **`Main`**: Source project loader (Folder/ZIP), progress indicator, local & LAN preview links, and build logs.
  - **`Temp Build`**: Ephemeral workspace for quick testing with automatic cleanup on close or next build.
  - **`Builds List`**: All compiled builds with double-click browser preview, right-click "Open Project Location", and Recycle Bin deletion.
  - **`Requirenments`**: Real-time Node.js/npm detection, direct download installer button, online version check, and re-check.
  - **`Settings`**: Port configuration and quick explorer links for projects, builds, and AppData directories.
  - **`About`**: Project information, credits, and YouTube links.
- **Automatic Missing Node.js Prompt**: On launch, if Node.js is not detected, an instant dialog appears offering **"Download Directly"** (fetches official Windows installer and executes it) or **"Website"** for manual download.
- **Drag-and-Drop Workflow**: Drop any ZIP archive or folder downloaded from Google AI Studio, Bolt, or v0 directly into the application.
- **1-Click Local Build**: Automatically installs node packages and compiles your React, Vite, or Next.js app seamlessly.
- **Dynamic Multi-Port Hosting**: Preview multiple projects simultaneously on local server ports without port collision errors.
- **Safe Recycle Bin Deletion**: Deleting builds moves project directories and archive files directly into your Windows Recycle Bin.
- **Open Project Location**: Right-click any build to instantly jump to its storage folder in Windows File Explorer.
- **Zero Terminal Required**: Built specifically for prompt designers and creators to fix blank screen issues instantly.

---

## 🚀 Why Flash npmBuilder over Visual Studio Code?

| Feature | Visual Studio Code | Flash npmBuilder |
| :--- | :--- | :--- |
| **Setup Complexity** | Heavy (Extensive configurations, extensions, terminal) | **Zero-config portable standalone GUI** |
| **Workflow** | Manual `cd`, `npm install`, `npm run dev` / `npm run build` | **1-Click automatic compile and preview** |
| **Port Conflicts** | Frequent `EADDRINUSE` errors if port 3000 is occupied | **Automatic dynamic port selection & multi-instance routing** |
| **File Management** | Manual file deletion leaves orphaned caches & temp files | **Precise Recycle Bin integration & Ephemeral Temp cleans** |
| **Target Audience** | Software engineers and developers | **Prompt creators, designers, and non-technical users** |

---

## 📥 Download & Install

1. Download `Flash-npmBuilder-v1.02.zip` from the Assets below.
2. Extract the folder and run `Flash-npmBuilder.exe`.
3. No installation or global setup required!

---

## 💻 Running from Source / Testing

If you are developing or testing Flash npmBuilder from source:

### Prerequisites:
- Windows 10 or Windows 11
- Python 3.10+
- Node.js installed ([Download Current Node.js](https://nodejs.org/en/download/current))

### Quick Launch:
Double-click `run_test.bat` or run:
```bash
pip install -r requirements.txt
python app.py
```

---

## 🛠️ Building the Standalone Portable Executable

To compile a portable standalone `.exe` with PyInstaller:

1. Double-click `build_exe.bat`.
2. The compilation script will bundle all dependencies into `dist\Flash-npmBuilder\Flash-npmBuilder.exe`.

---

## 📂 Storage Architecture (AppData Directory Structure)

All project configurations, cache, temporary builds, and compiled releases are organized cleanly under the user's Windows AppData directory:

```
%APPDATA%\Flash_npmBuilder\
├── config\
│   └── settings.json        # User configurations & port preferences
├── projects\                # Active build working trees
├── builds\                  # Compiled production builds & zip packages
│   └── builds.json          # Builds registry metadata
├── temp\                    # Ephemeral temp build directory (auto-purged)
└── cache\                   # Zip extraction buffers
```

---

## 📜 License & Copyright

Distributed under the MIT Open Source License.

Copyright (c) 2026 **Tech Realtime** & **SaQuiz Perks**. Conceived and Designed by **Mr. Saqlain**.
YouTube: https://www.youtube.com/@TechRealtime
