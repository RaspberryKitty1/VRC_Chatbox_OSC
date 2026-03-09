# 🗨️ VRChat Spotify, YouTube & System Stats Chatbox Integration

Display your **Spotify now-playing**, **YouTube/Twitch playback info**, and **real-time system stats** (CPU, GPU, RAM, local time) directly in your **VRChat chatbox** using **OSC (Open Sound Control)**. Includes a **tray icon** for live switching between display modes — runs silently in the system tray with minimal overhead.

---

![UV](https://img.shields.io/badge/dependencies-uv-brightgreen)
![Python](https://img.shields.io/badge/python-3.14+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Windows](https://img.shields.io/badge/platform-Windows-blue)

## 🚀 Features

* 🎵 Real-time Spotify playback info with progress updates

* 📺 YouTube & Twitch info via WebSocket from a browser extension

* 🖥️ System stats: CPU, GPU (NVIDIA only), RAM, and local time

* 🧠 Smart updates — sends messages to VRChat **only when content changes**

* 🪟 Tray icon for easy switching between display modes

* 📡 WebSocket server runs only in relevant modes

* 💡 Display Modes:

  * `full` — System stats + Spotify + Media info (default)
  * `system` — System stats only
  * `spotify` — Spotify playback only
  * `media` — YouTube/Twitch playback only

* 🔐 Uses `.env` for secure Spotify credentials

* 🪶 Runs cleanly in the background with tray-only interface

* 🔁 Handles Spotify or GPU unavailability gracefully

---

## 🧰 Requirements

* Windows
* UV
* VRChat with OSC enabled
  *(Settings → OSC → Enable OSC & note your local IP)*

Optional:

* Spotify account + Developer App
* Firefox/Chrome + [Media Info Extractor Extension/User Script](https://github.com/RaspberryKitty1/VRC-OSC-Media-Companion)
* NVIDIA GPU for GPU stats (`nvidia-ml-py`)

---

## 🛠️ Installation

This project uses **uv** for dependency management instead of `pip`.

**Python 3.14+ is required.**

`uv` handles:

* virtual environments
* dependency installation
* Python version management
* running the project

---

### 1. Download the Project

1. Option A — Download ZIP (recommended for most users)

   1. Click **Code → Download ZIP** on the GitHub repository page.
   2. Extract the ZIP file.
   3. Open a terminal inside the extracted folder.

2. Option B — Clone with Git

   ```bash
   git clone https://github.com/RaspberryKitty1/VRC_Chatbox_OSC.git
   cd VRC_Chatbox_OSC
   ```

### 2. Install `uv` (Windows)

Open **PowerShell** and run:

```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

Documentation: <https://docs.astral.sh/uv/>

### 3. Install Dependencies

```bash
uv sync
```

---

## ⚙️ Configuration

Create a `.env` file in the project root with:

```dotenv
SPOTIPY_CLIENT_ID=your-client-id
SPOTIPY_CLIENT_SECRET=your-client-secret
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
VRCHAT_IP=127.0.0.1
```

> To get `SPOTIPY_CLIENT_ID` and `SPOTIPY_CLIENT_SECRET`, create an app in the Spotify Developer Dashboard.
>
> **Note:** Spotify apps run in Development Mode by default and require a **Spotify Premium account** for API access. (effective March 9, 2026)
>
> Set the Redirect URI in your Spotify app to:
> `http://127.0.0.1:8888/callback`

---

## 🎥 YouTube/Twitch & Spotify Integration

* **YouTube/Twitch Media:**

  1. Install the [Media Info Extractor Extension/User Script](https://github.com/RaspberryKitty1/VRC-OSC-Media-Companion) in your browser.
  2. Play a video on YouTube or Twitch.
  3. Switch your tray icon to `media` **or `full`** mode to see video info in VRChat.

     > The extension sends live info to `ws://localhost:12345`, which this app receives and forwards to VRChat. Updates appear almost instantly in chat.

* **Spotify Playback:**

  * Displays song, artist, and playback progress.
  * Updates every few seconds (default fetch interval is ~15 s), so there may be a slight delay in reflecting current playback or position.
  * Must be actively playing to show info.

---

## 🖥️ Running the App

```bash
uv run osc.py
```

### 🔕 Run Silently (No Console Window)

**Option A: Use `.pyw`**

```bash
start "" .venv\Scripts\pythonw.exe vrchat_status_tray.pyw
```

**Option B: Build a `.exe` with PyInstaller**

```bash
pyinstaller --noconsole --onefile --icon=chat_bubble.ico vrchat_status_tray.py
```

> Output will be in the `dist/` folder.

---

## 💬 Tray Icon & Display Modes

Right-click the tray icon to choose:

| Mode      | Description                                   |
| --------- | --------------------------------------------- |
| `full`    | System stats + Spotify + Media info (default) |
| `system`  | CPU, GPU, RAM, local time only                |
| `spotify` | Spotify song + artist + progress              |
| `media`   | YouTube/Twitch title + uploader + timestamp   |
| `Quit`    | Cleanly exits the app                         |

> Updates are sent every 2 seconds **only if content changed**, reducing OSC spamming.

---

## 📝 Notes

* 🎵 Spotify must be running and actively playing to show info
* 📺 YouTube/Twitch support requires the Media Info Extractor Extension
* 🔹 GPU stats are available only if using NVIDIA and `pynvml` is installed
* 🔄 Spotify tokens are auto-refreshed and cached locally
* 🧼 OSC messages are deduplicated to minimize traffic
* ⏱ Spotify may have a small delay (~15 s) due to API fetch intervals

---

## 📜 License

Licensed under the [MIT License](LICENSE)

---

## 🤝 Contribute

Feedback, bug reports, and contributions are welcome via [Issues](https://github.com/RaspberryKitty1/VRC-OSC-Media-Companion/issues) or Pull Requests.
