# 🗨️ VRChat Spotify + System Stats Chatbox Integration

Display your **Spotify now-playing info** and **system stats** (CPU, GPU, RAM, local time) directly in your **VRChat chatbox** using **OSC (Open Sound Control)**. Includes a **tray icon** for live mode switching with no console window!

---

## 🚀 Features

* Displays local time in 12-hour format
* Real-time CPU, GPU (NVIDIA), and RAM usage
* Current Spotify song info with timestamp progress
* **Tray icon with chat bubble + live mode switching**
* Three display modes: full (default), system-only, or Spotify-only
* Smart update system (only sends when content changes)
* Uses `.env` for secure Spotify API credentials
* Graceful fallback if no Spotify or GPU data available
* Can be hidden from view (no console window)

---

## 🧰 Requirements

* Python 3.7+
* Spotify account + Developer App
* VRChat with OSC enabled
  (Enable in: **Settings > OSC > Enable OSC**)
* Windows with optional:

  * NVIDIA GPU for GPU stats (fallbacks to N/A if unavailable)

---

## 📦 Setup

### 1. Clone or download this repository

```bash
git clone https://github.com/raspberryKitty1/vrchat-status-overlay.git
cd vrchat-status-overlay
```

---

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

---

### 3. Create a Spotify Developer App

* Visit: [https://developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
* Create an app
* Set Redirect URI to:

```plaintext
http://127.0.0.1:8888/callback
```

> ⚠️ Use `127.0.0.1`, not `localhost`, to avoid redirect issues.

---

### 4. Add your credentials to `.env`

Create a file named `.env` in the project folder:

```dotenv
SPOTIPY_CLIENT_ID=your-client-id
SPOTIPY_CLIENT_SECRET=your-client-secret
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
VRCHAT_IP=127.0.0.1
```

---

### 5. Run the app (console version)

```bash
python vrchat_status_tray.py
```

---

## 🖥️ No Console Mode (Tray App)

If you want the script to **run silently in the tray**:

### ➤ Option A: Rename to `.pyw` and run with `pythonw`

1. Rename `vrchat_status_tray.py` → `vrchat_status_tray.pyw`
2. Launch using:

```bat
start "" venv\Scripts\pythonw.exe vrchat_status_tray.pyw
```

---

### ➤ Option B: Build as `.exe` with PyInstaller

```bash
pyinstaller --noconsole --onefile --icon=chat_bubble.ico vrchat_status_tray.py
```

Your `.exe` will appear in the `dist/` folder and launch with a tray icon and no visible window.

---

## 📋 Usage: Tray & Modes

When launched, the app places a **chat bubble icon** in your system tray. Right-click to choose:

| Mode      | Description                |
| --------- | -------------------------- |
| `full`    | System + Spotify (default) |
| `system`  | System stats only          |
| `spotify` | Spotify info only          |
| `Quit`    | Cleanly exits the app      |

🟢 The tray updates the VRChat chatbox every 2 seconds if the content has changed.

---

> [!NOTE]
>
> * 🎵 **Spotify** must be running and playing to show track info
> * 📉 **GPU stats** require an NVIDIA GPU + `pynvml`
> * ⏸️ If nothing is playing, it shows “Nothing playing”
> * 🧠 Spotify info is cached to reduce API calls (15s max delay)
> * 🧼 Output avoids spam by only sending updates when content changes
> * 🔒 Your Spotify tokens are cached and refreshed automatically

---

## 🧾 License

MIT License — see [LICENSE](LICENSE)

---

## 🤝 Contributions

Pull requests and issues welcome!
Feel free to contribute improvements, bug fixes, or feature suggestions.

