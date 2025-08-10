# 🗨️ VRChat Spotify, YouTube & System Stats Chatbox Integration

Display your **Spotify now-playing**, **YouTube/Twitch playback info**, and **real-time system stats** (CPU, GPU, RAM, local time) in your **VRChat chatbox** using **OSC (Open Sound Control)**. Features a **tray icon** for live mode switching — runs silently in the system tray with minimal overhead.

---

## 🚀 Features

* 🎵 Spotify playback with real-time progress updates
* 📺 YouTube & Twitch info via WebSocket from browser extension
* 🖥️ System stats: CPU, GPU (NVIDIA only), RAM, and local time
* 🧠 Smart updates — sends to VRChat only when content changes
* 🪟 Tray icon for live switching between display modes
* 📡 WebSocket server runs only in relevant modes
* 💡 Display Modes:

  * `full` — All info combined (default)
  * `system` — System stats only
  * `spotify` — Spotify playback only
  * `media` — YouTube/Twitch playback only
* 🔐 Uses `.env` for secure Spotify credentials
* 🪶 Clean background execution with tray-only interface
* 🔁 Handles Spotify/GPU unavailability gracefully

---

## 🧰 Requirements

* Windows
* Python 3.7+
* VRChat with OSC enabled
  *(VRChat > Settings > OSC > Enable OSC & note your IP)*
* Optional:

  * Spotify account + Developer App
  * Firefox/Chrome + [Media Info Extractor Extension/User Script](https://github.com/RaspberryKitty1/VRC-OSC-Media-Companion)
  * NVIDIA GPU for GPU stats (`pynvml`)

---

## 📦 Setup

### 1. Clone the Repository

```bash
git clone https://github.com/RaspberryKitty1/VRC_Chatbox_OSC.git
cd VRC_Chatbox_OSC
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure `.env`

Create a `.env` file in the root folder with:

```dotenv
SPOTIPY_CLIENT_ID=your-client-id
SPOTIPY_CLIENT_SECRET=your-client-secret
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
VRCHAT_IP=127.0.0.1
```

To get `SPOTIPY_CLIENT_ID` and `SPOTIPY_CLIENT_SECRET`, create a [Spotify Developer App](https://developer.spotify.com/dashboard).

Set the **Redirect URI** in your Spotify app to:

```plaintext
http://127.0.0.1:8888/callback
```

---

## 🎥 YouTube/Twitch Media Integration

To show YouTube or Twitch video info:

1. Install the [Media Info Extractor Extension/User Script](https://github.com/RaspberryKitty1/VRC-OSC-Media-Companion) in Firefox
2. Play a video on YouTube or Twitch
3. Right-click the tray icon and select `media` mode

> The extension sends live info to `ws://localhost:12345`, which this app receives and forwards to VRChat.

---

## 🖥️ Run the App

```bash
python vrchat_status_tray.py
```

---

## 🔕 Run Silently (No Console Window)

### Option A: Rename to `.pyw` and use `pythonw`

```bash
start "" venv\Scripts\pythonw.exe vrchat_status_tray.pyw
```

### Option B: Build `.exe` with PyInstaller

```bash
pyinstaller --noconsole --onefile --icon=chat_bubble.ico vrchat_status_tray.py
```

Output will be in the `dist/` folder.

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

> ✅ Updates are sent every 2 seconds **only if something changed**, avoiding OSC spamming.

---

## 📝 Notes

* 🎵 Spotify must be running & actively playing to show info
* 📺 YouTube/Twitch support requires the **Media Info Extractor Extension**
* 📉 GPU stats are shown only if using NVIDIA and `pynvml` is installed
* 🔄 Spotify tokens are auto-refreshed and cached locally
* 🧼 OSC messages are smartly deduplicated to minimize chatter

---

## 📜 License

Licensed under the [MIT License](LICENSE)

---

## 🤝 Contribute

Feedback, bug reports, and contributions are welcome via [Issues](https://github.com/RaspberryKitty1/VRC_Chatbox_OSC/issues) or PRs!


