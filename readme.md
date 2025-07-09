# VRChat Spotify + System Stats Chatbox Integration

Send your Spotify now-playing info along with your system stats (CPU, GPU, RAM, and local time) directly into the VRChat chatbox using VRChat's OSC interface.

---

## Features

- Displays current time (12-hour format)
- Shows CPU, GPU (NVIDIA), and RAM usage
- Shows Spotify currently playing song with progress time
- **Toggle output modes:** full (default), system-only, or Spotify-only
- Updates safely every 2 seconds to avoid VRChat message loss
- Uses environment variables to securely manage Spotify API credentials
- Gracefully handles missing GPU or Spotify data

---

## Requirements

- Python 3.7+
- VRChat running with OSC enabled (Settings > OSC)
- Spotify account
- NVIDIA GPU for GPU usage (optional; falls back gracefully if none)

---

## Setup

1. **Clone or download this repo**

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Create a Spotify Developer App**

   - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)

   - Create a new app

   - Set the Redirect URI to:
     `http://127.0.0.1:8888/callback`

     > ⚠️ Spotify is deprecating `localhost`. Use `127.0.0.1` instead.

   - Note your **Client ID** and **Client Secret**

4. **Create a `.env` file**

   In the project folder, create a `.env` file:

   ```dotenv
   SPOTIPY_CLIENT_ID=your-client-id
   SPOTIPY_CLIENT_SECRET=your-client-secret
   SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
   ```

5. **Run the script**

   ```bash
   python vrchat_system_spotify_status.py
   ```

---

## Usage

By default, the script sends **both** system stats and Spotify song info to the VRChat chatbox.

### 🛠 Mode Selection (Optional)

Use the `--mode` flag to control what gets shown:

| Mode      | Description                |
| --------- | -------------------------- |
| `full`    | (Default) System + Spotify |
| `system`  | System stats only          |
| `spotify` | Spotify info only          |

### Example

```bash
python vrchat_system_spotify_status.py --mode spotify
```

---

> [!NOTE]
>
> - GPU usage requires an NVIDIA GPU and `pynvml` installed
> - If GPU is not detected, GPU usage will show as `N/A`
> - If nothing is playing on Spotify, a pause message is sent
> - Avoid spamming the chatbox: the script only sends updates when content changes

---

## 📄 License

This project is licensed under the **MIT License**.
See the [LICENSE](LICENSE) file for full details.

---

## Contributions

Pull requests and issue reports are welcome!
If you have ideas, improvements, or fixes — feel free to contribute!
