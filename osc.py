import os
import time
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from pythonosc.udp_client import SimpleUDPClient

# === Load secrets from .env file ===
load_dotenv()

client_id = os.getenv("SPOTIPY_CLIENT_ID")
client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI")

# === VRChat OSC Setup ===
VRCHAT_IP = "127.0.0.1"
VRCHAT_PORT = 9000
OSC_ADDRESS = "/chatbox/input"
client = SimpleUDPClient(VRCHAT_IP, VRCHAT_PORT)

# === Spotify Auth Setup ===
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope="user-read-playback-state"
))

def format_time(ms):
    """Convert milliseconds to M:SS format"""
    seconds = int(ms / 1000)
    minutes = seconds // 60
    return f"{minutes}:{str(seconds % 60).zfill(2)}"

def get_spotify_message():
    """Get a compact, clean Spotify message for VRChat"""
    try:
        current = sp.current_playback()
        if current and current.get("is_playing", False):
            track = current["item"]
            song = track["name"]
            artist = ", ".join(a["name"] for a in track["artists"])
            progress_ms = current["progress_ms"]
            duration_ms = track["duration_ms"]

            progress = format_time(progress_ms)
            duration = format_time(duration_ms)
            percent = int((progress_ms / duration_ms) * 100)

            return f"🎵 {song} by {artist}\n{percent}% ({progress} / {duration})"
        else:
            return "⏸️ Nothing is playing on Spotify."
    except Exception as e:
        return f"⚠️ Spotify error"

def send_to_vrchat(message):
    """Send message to VRChat chatbox"""
    client.send_message(OSC_ADDRESS, [message, True])
    print("Sent:", message)

# === Main Loop ===
if __name__ == "__main__":
    print("🚀 Spotify → VRChat started")
    last_message = ""
    try:
        while True:
            message = get_spotify_message()
            if message != last_message:
                send_to_vrchat(message)
                last_message = message
            time.sleep(2)  # Safe minimum interval
    except KeyboardInterrupt:
        print("🛑 Stopped by user.")
