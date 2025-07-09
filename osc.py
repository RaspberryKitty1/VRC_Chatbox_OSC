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

# === OSC Client (VRChat) Setup ===
VRCHAT_IP = "127.0.0.1"
VRCHAT_PORT = 9000
OSC_ADDRESS = "/chatbox/input"
client = SimpleUDPClient(VRCHAT_IP, VRCHAT_PORT)

# === Spotify API Auth ===
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope="user-read-playback-state"
))

def format_time(ms):
    """Convert milliseconds to M:SS"""
    seconds = int(ms / 1000)
    minutes = seconds // 60
    return f"{minutes}:{str(seconds % 60).zfill(2)}"

def create_progress_bar(progress_ms, duration_ms, bar_length=10):
    """Create a ▮▯ style progress bar"""
    if duration_ms == 0:
        return "▯" * bar_length
    percent = progress_ms / duration_ms
    filled = round(percent * bar_length)
    return "▮" * filled + "▯" * (bar_length - filled)

def get_spotify_info():
    """Get current song and progress"""
    try:
        current = sp.current_playback()
        if current and current.get("is_playing", False):
            track = current["item"]
            song = track["name"]
            artist = ", ".join(a["name"] for a in track["artists"])
            progress_ms = current["progress_ms"]
            duration_ms = track["duration_ms"]
            bar = create_progress_bar(progress_ms, duration_ms)
            progress = format_time(progress_ms)
            duration = format_time(duration_ms)
            return f"🎵 {song} by {artist}\n{bar} ({progress} / {duration})"
        else:
            return "⏸️ Nothing is playing on Spotify."
    except Exception as e:
        return f"⚠️ Spotify error: {str(e)}"

def send_to_vrchat(msg):
    """Send message to VRChat chatbox"""
    client.send_message(OSC_ADDRESS, [msg, True])
    print("Sent:", msg)

# === Main Loop ===
if __name__ == "__main__":
    print("Starting Spotify → VRChat Chatbox...")
    last_msg = ""
    try:
        while True:
            msg = get_spotify_info()
            if msg != last_msg:
                send_to_vrchat(msg)
                last_msg = msg
            time.sleep(1)  # Update every second
    except KeyboardInterrupt:
        print("Stopped by user.")
