import os
import time
from datetime import datetime
import argparse
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from pythonosc.udp_client import SimpleUDPClient
import psutil

# === Optional: Try to import GPU usage via pynvml ===
try:
    import pynvml
    pynvml.nvmlInit()
    gpu_available = True
except:
    gpu_available = False

# === Load .env variables ===
load_dotenv()
client_id = os.getenv("SPOTIPY_CLIENT_ID")
client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI")

# === VRChat OSC Setup ===
VRCHAT_IP = "127.0.0.1"
VRCHAT_PORT = 9000
OSC_ADDRESS = "/chatbox/input"
client = SimpleUDPClient(VRCHAT_IP, VRCHAT_PORT)

# === Spotify Setup ===
auth_manager = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope="user-read-playback-state"
)

def get_spotify_client():
    token_info = auth_manager.get_cached_token()
    if not token_info or auth_manager.is_token_expired(token_info):
        try:
            token_info = auth_manager.refresh_access_token(token_info['refresh_token'])
        except Exception as e:
            print(f"[Spotify Refresh Error] {e}")
            return None
    return spotipy.Spotify(auth=token_info['access_token'])

def format_time(ms):
    seconds = int(ms / 1000)
    minutes = seconds // 60
    return f"{minutes}:{str(seconds % 60).zfill(2)}"

# Cache for Spotify playback info
spotify_cache = {
    "song": None,
    "artist": None,
    "duration_ms": 0,
    "last_progress_ms": 0,
    "last_fetch_time": 0,
    "is_playing": False
}

def fetch_spotify_playback(max_retries=3, delay=2):
    """Fetch fresh playback info from Spotify with retry and update cache."""
    for attempt in range(1, max_retries + 1):
        try:
            client = get_spotify_client()
            if not client:
                return False
            current = client.current_playback()
            if current and current.get("is_playing", False) and current["item"]:
                track = current["item"]
                spotify_cache["song"] = track["name"]
                spotify_cache["artist"] = ", ".join(a["name"] for a in track["artists"])
                spotify_cache["duration_ms"] = track["duration_ms"]
                spotify_cache["last_progress_ms"] = current["progress_ms"]
                spotify_cache["last_fetch_time"] = time.time()
                spotify_cache["is_playing"] = True
                return True
            else:
                spotify_cache["is_playing"] = False
                return False
        except Exception as e:
            print(f"[Attempt {attempt}/{max_retries}] Spotify Fetch Error: {e}")
            if attempt < max_retries:
                time.sleep(delay * attempt)  # Exponential backoff
            else:
                return False

def get_spotify_message_with_progress_update(fetch_interval=15):
    """Update progress locally, fetch fresh data every fetch_interval seconds or if song ended."""
    now = time.time()
    time_since_fetch = now - spotify_cache["last_fetch_time"]

    if spotify_cache["is_playing"]:
        elapsed = time_since_fetch * 1000  # ms
        current_progress = int(spotify_cache["last_progress_ms"] + elapsed)

        # Force refresh immediately if song ended or progress >= duration
        if current_progress >= spotify_cache["duration_ms"]:
            success = fetch_spotify_playback()
            if not success:
                return "⏸️ Nothing playing"
        elif time_since_fetch > fetch_interval:
            success = fetch_spotify_playback()
            if not success:
                return "⏸️ Nothing playing"
    else:
        # If not playing, refresh periodically to detect changes
        if time_since_fetch > fetch_interval:
            success = fetch_spotify_playback()
            if not success:
                return "⏸️ Nothing playing"

    # After possible refresh, update progress display
    if spotify_cache["is_playing"]:
        elapsed = time.time() - spotify_cache["last_fetch_time"]
        current_progress = int(spotify_cache["last_progress_ms"] + elapsed * 1000)
        if current_progress > spotify_cache["duration_ms"]:
            current_progress = spotify_cache["duration_ms"]

        progress_str = format_time(current_progress)
        duration_str = format_time(spotify_cache["duration_ms"])
        return f"🎵 {spotify_cache['song']} by {spotify_cache['artist']}\n{progress_str} / {duration_str}"
    else:
        return "⏸️ Nothing playing"

def get_system_stats():
    """Returns system info string (CPU, GPU, RAM, time)"""
    now = datetime.now().strftime("🕒 %I:%M %p")
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    gpu = "N/A"
    if gpu_available:
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            gpu = f"{util.gpu}%"
        except Exception as e:
            print(f"[GPU Error] {e}")
            gpu = "Err"
    return f"{now}\nCPU:{cpu:.0f}% | GPU:{gpu} | RAM:{ram:.0f}%"

def send_to_vrchat(msg):
    client.send_message(OSC_ADDRESS, [msg, True])
    print("Sent:\n" + msg + "\n" + "-"*30)

# === Command-line argument parsing ===
parser = argparse.ArgumentParser(description="VRChat System + Spotify Status")
parser.add_argument(
    "--mode",
    choices=["full", "system", "spotify"],
    default="full",
    help="Select what to display: full (default), system, or spotify"
)
args = parser.parse_args()

# === Main Loop ===
if __name__ == "__main__":
    print(f"🚀 VRChat System + Spotify status started (Mode: {args.mode})")
    last_message = ""
    try:
        while True:
            system_info = get_system_stats()
            song_info = get_spotify_message_with_progress_update()

            if args.mode == "full":
                full_message = system_info + "\n\n" + (song_info or "⏸️ Nothing playing")
            elif args.mode == "system":
                full_message = system_info
            elif args.mode == "spotify":
                full_message = song_info or "⏸️ Nothing playing"

            if full_message != last_message:
                send_to_vrchat(full_message)
                last_message = full_message

            time.sleep(2)
    except KeyboardInterrupt:
        print("🛑 Stopped by user.")
