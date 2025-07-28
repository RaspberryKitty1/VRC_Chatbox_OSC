# 🗨️ VRChat Spotify, YouTube & System Stats Chatbox Integration

Display your **Spotify now-playing**, **YouTube playback info**, and **real-time system stats** (CPU, GPU, RAM, local time) in your **VRChat chatbox** using **OSC (Open Sound Control)**. Features a **tray icon** for live mode switching and no console window clutter.

---

## 🚀 Features

* 🎵 Spotify playback info with timestamp progress
* 📺 YouTube video info via browser extension
* 🖥️ System stats: CPU, GPU (NVIDIA), RAM, and local time
* 🟢 Smart OSC updates: only sends when data changes
* 💬 Tray icon with live display mode switching
* 💡 Four modes:

  * `full` — All info (default)
  * `system` — System stats only
  * `spotify` — Spotify only
  * `youtube` — YouTube video only
* 🔐 Uses `.env` for secure Spotify credentials
* 🪶 Runs silently in system tray (no console window)
* 🔁 Fallbacks gracefully if Spotify or GPU data unavailable

---

## 🧰 Requirements

* Windows
* Python 3.7+
* VRChat with OSC enabled
  *(Settings > OSC > Enable OSC)*
* Optional:

  * **Spotify account** + Developer App
  * **Firefox** + [YouTube Media Info Extractor](https://github.com/RaspberryKitty1/VRC-OSC-Youtube-Companion)
  * **NVIDIA GPU** for GPU usage stats

---

## 📦 Setup

### 1. Clone the Repository

```bash
git clone https://github.com/RaspberryKitty1/VRC_Chatbox_OSC.git
cd vrchat-status-overlay
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Spotify

1. Create a Spotify Developer App:
   [https://developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)

2. Set the redirect URI to:

   ```plaintext
   http://127.0.0.1:8888/callback
   ```

3. Create a `.env` file in the project folder:

   ```dotenv
   SPOTIPY_CLIENT_ID=your-client-id
   SPOTIPY_CLIENT_SECRET=your-client-secret
   SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
   VRCHAT_IP=127.0.0.1
   ```

---

## 🎥 YouTube Integration

To display **YouTube video info** in VRChat:

1. Install the [YouTube Media Info Extractor](https://github.com/RaspberryKitty1/VRC_Chatbox_OSC) Firefox extension
2. Start a YouTube video in Firefox
3. Right-click the tray icon and switch to `youtube` mode

> 📡 The extension sends data to `ws://localhost:12345`, which this app receives and forwards to VRChat.

---

## 🖥️ Run the App (Console)

```bash
python vrchat_status_tray.py
```

---

## 🔕 Run Silently (No Console Window)

### Option A: `.pyw` + `pythonw`

1. Rename:
   `vrchat_status_tray.py` → `vrchat_status_tray.pyw`
2. Launch with:

```bat
start "" venv\Scripts\pythonw.exe vrchat_status_tray.pyw
```

### Option B: Compile `.exe` with PyInstaller

```bash
pyinstaller --noconsole --onefile --icon=chat_bubble.ico vrchat_status_tray.py
```

Output will be in `dist/`.

---

## 💬 Tray Icon & Display Modes

Right-click the tray icon to switch modes:

| Mode      | Description                              |
| --------- | ---------------------------------------- |
| `full`    | System stats + Spotify/YouTube (default) |
| `system`  | CPU, GPU, RAM, local time only           |
| `spotify` | Spotify song info only                   |
| `youtube` | YouTube video title + timestamp only     |
| `Quit`    | Cleanly exits the app                    |

📡 Updates are sent every 2 seconds **only if content changes**, reducing OSC spam.

---

## 📝 Notes

* 🎵 Spotify must be running and playing to show song info
* 📺 YouTube support requires Firefox + browser extension
* 📉 GPU stats require an NVIDIA GPU and `pynvml`
* 🔒 Spotify tokens are cached and refreshed automatically
* 🧼 Output avoids clutter by only updating when needed

---

## 📜 License

Licensed under the [MIT License](LICENSE)

---

## 🤝 Contribute

Issues, PRs, and ideas are always welcome!
