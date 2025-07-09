import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from pythonosc.udp_client import SimpleUDPClient

# === VRChat OSC Setup ===
VRCHAT_IP = "127.0.0.1"
VRCHAT_PORT = 9000
OSC_ADDRESS = "/chatbox/input"
client = SimpleUDPClient(VRCHAT_IP, VRCHAT_PORT)

# === Spotify API Setup ===
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    redirect_uri="http://localhost:8888/callback",
    scope="user-read-playback-state"
))

def format_time(ms):
    """Convert milliseconds to M:SS format"""
    seconds = int(ms / 1000)
    minutes = seconds // 60
    return f"{minutes}:{str(seconds % 60).zfill(2)}"

def get_spotify_info():
    """Fetch current playing track info from Spotify"""
    current = sp.current_playback()

    if current and current['is_playing']:
        song = current['item']['name']
        artist = ", ".join([a['name'] for a in current['item']['artists']])
        progress = format_time(current['progress_ms'])
        duration = format_time(current['item']['duration_ms'])
        return f"🎵 {song} by {artist}\n{progress} | {duration}"
    else:
        return "⏸️ Nothing is playing on Spotify."

def send_to_vrchat(msg):
    """Send a message to VRChat chatbox"""
    client.send_message(OSC_ADDRESS, [msg, True])
    print("Sent:", msg)

# === Loop: Check every 10 seconds ===
try:
    last_message = ""
    while True:
        msg = get_spotify_info()
        if msg != last_message:
            send_to_vrchat(msg)
            last_message = msg
        time.sleep(10)  # Check every 10 seconds
except KeyboardInterrupt:
    print("Stopped.")
