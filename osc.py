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
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope="user-read-playback-state"
))

# === Command-line argument parsing ===
parser = argparse.ArgumentParser(description="VRChat System + Spotify Status")
parser.add_argument(
    "--mode",
    choices=["full", "system", "spotify"],
    default="full",
    help="Select what to display: full (default), system, or spotify"
)
args = parser.parse_args()

def format_time(ms):
    seconds = int(ms / 1000)
    minutes = seconds // 60
    return f"{minutes}:{str(seconds % 60).zfill(2)}"

def get_spotify_message():
    """Returns song info if playing, or empty string."""
    try:
        current = sp.current_playback()
        if current and current.get("is_playing", False):
            track = current["item"]
            song = track["name"]
            artist = ", ".join(a["name"] for a in track["artists"])
            progress = format_time(current["progress_ms"])
            duration = format_time(track["duration_ms"])
            return f"🎵 {song} by {artist}\n{progress} / {duration}"
    except Exception as e:
        print(f"[Spotify Error] {e}")
    return ""

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

# === Main Loop ===
if __name__ == "__main__":
    print(f"🚀 VRChat System + Spotify status started (Mode: {args.mode})")
    last_message = ""
    try:
        while True:
            system_info = get_system_stats()
            song_info = get_spotify_message()

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
