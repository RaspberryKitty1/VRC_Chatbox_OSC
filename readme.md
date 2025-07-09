# VRChat Spotify + System Stats Chatbox Integration

Send your Spotify now-playing info along with your system stats (CPU, GPU, RAM, and local time) directly into the VRChat chatbox using VRChat's OSC interface.

---

## Features

- Displays current time (12-hour format)
- Shows CPU, GPU (NVIDIA), and RAM usage
- Shows Spotify currently playing song with progress time
- Updates safely every 2 seconds to avoid VRChat message loss
- Uses environment variables to securely manage Spotify API credentials

---

## Requirements

- Python 3.7+
- VRChat running with OSC enabled (Settings > OSC)
- Spotify account
- NVIDIA GPU for GPU usage (optional; falls back gracefully if none)

---

## Setup

1. **Clone or download this repo**

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

1. **Create a Spotify Developer App**

   - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   - Create a new app
   - Set Redirect URI to `http://127.0.0.1:8888/callback`
   - Note your `Client ID` and `Client Secret`

1. **Create a `.env` file**

   In the project folder, create a `.env` file:

   ```dotenv
   SPOTIPY_CLIENT_ID=your-client-id
   SPOTIPY_CLIENT_SECRET=your-client-secret
   SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
   ```

1. **Run the script**

   ```bash
   python vrchat_system_spotify_status.py
   ```

---

## Usage

- Make sure VRChat is running with OSC enabled
- Play music on Spotify
- The script will automatically send updates to your VRChat chatbox every 2 seconds

---

> [!NOTE]
>
> - GPU usage requires an NVIDIA GPU and `pynvml` installed
> - The script handles missing GPU info gracefully
> - If nothing is playing on Spotify, a pause message is sent

---

## 📄 License

This project is licensed under the **MIT License**.
See the [LICENSE](LICENSE) file for full details.

---

## Contributions

Feel free to open issues or submit pull requests for improvements or bug fixes!
