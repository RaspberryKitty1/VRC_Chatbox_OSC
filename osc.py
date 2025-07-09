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

def create_progress_bar(progress_ms, duration_ms, bar_length=10):
    """Return a bar like ▮▮▯▯▯▯▯▯▯▯"""
    percent = progress_ms / duration_ms
    filled = round(percent * bar_length)
    return '▮' * filled + '▯' * (bar_length - filled)

def get_spotify_info():
    """Fetch current playing track info from Spotify"""
    current = sp.current_playback()

    if current and current['is_playing']:
        song = current['item']['name']
        artist = ", ".join([a['name'] for a in current['item']['artists']])
        progress_ms = current['progress_ms']
        duration_ms = current['item']['duration_ms']

        progress_bar = create_progress_bar(progress_ms, duration_ms)
        progress = format_time(progress_ms)
        duration = format_time(duration_ms)

        message = f"🎵 {song} by {artist}\n{progress_bar} ({progress} / {duration})"
        return message
    else:
        return "⏸️ Nothing is playing on Spotify."

def send_to_vrchat(msg):
    """Send a message to VRChat chatbox"""
    client.send_message(OSC_ADDRESS, [msg, True])
    print("Sent:", msg)

# === Main Loop ===
try:
    last_message = ""
    while True:
        msg = get_spotify_info()
        if msg != last_message:
            send_to_vrchat(msg)
            last_message = msg
        time.sleep(1)  # Update every second
except KeyboardInterrupt:
    print("Stopped.")
