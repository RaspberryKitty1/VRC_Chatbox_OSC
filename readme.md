# VRChat Spotify + System Stats Chatbox Integration

Send your Spotify now-playing info along with your system stats (CPU, GPU, RAM, and local time) directly into the VRChat chatbox using VRChat's OSC interface.

---

## Features

* Displays current local time (12-hour format)
* Shows CPU, GPU (NVIDIA), and RAM usage in real-time
* Shows Spotify currently playing song with progress time
* **Toggle output modes:** full (default), system-only, or Spotify-only
* Updates every 2 seconds with change detection to avoid chat spam
* Uses environment variables to securely manage Spotify API credentials
* Gracefully handles missing GPU or Spotify data

---

## Requirements

* Python 3.7+
* VRChat running with OSC enabled (Settings > OSC)
* Spotify account
* NVIDIA GPU for GPU usage (optional; will fallback if unavailable)

---

## Setup

1. **Clone or download this repository**

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Create a Spotify Developer App**

   * Visit the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   * Create a new app
   * Set the Redirect URI to:

     ```plaintext
     http://127.0.0.1:8888/callback
     ```

     > ⚠️ Spotify recommends using `127.0.0.1` instead of `localhost`
   * Copy your **Client ID** and **Client Secret**

4. **Create a `.env` file**

   In your project folder, create a `.env` file containing:

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

### Mode Selection (Optional)

Use the `--mode` flag to control what gets sent:

| Mode      | Description                |
| --------- | -------------------------- |
| `full`    | (Default) System + Spotify |
| `system`  | System stats only          |
| `spotify` | Spotify info only          |

### Examples

Send Spotify info only:

```bash
python vrchat_system_spotify_status.py --mode spotify
```

Send system info only:

```bash
python vrchat_system_spotify_status.py --mode system
```

---

> [!NOTE]
>
> * **Spotify API calls are rate-limited and cached** to reduce usage. Because of this, updates such as song skips, pauses, or changes **may take up to 15 seconds to appear** in VRChat.
> * GPU usage requires an NVIDIA GPU and the `pynvml` Python package.
> * If no GPU is detected, GPU usage will display as `N/A`.
> * When Spotify is not playing anything, the chatbox shows a pause icon with the message "Nothing playing".
> * The script only sends messages when there is a change to prevent spamming VRChat’s chatbox.
> * Spotify tokens are cached and refreshed automatically.

---

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

## Contributions

Contributions are welcome! Feel free to open issues or submit pull requests for bugs, features, or improvements.
