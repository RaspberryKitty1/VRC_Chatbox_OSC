import os
import time
import threading
from datetime import datetime
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from pythonosc.udp_client import SimpleUDPClient
import psutil
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item

# === Optional GPU stats ===
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

# === Tray icon image ===
def create_chat_bubble_icon(size=64):
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    bubble_color = (30, 144, 255, 255)
    dot_color = (255, 255, 255, 255)
    
    radius = size // 6
    rect = [size * 0.125, size * 0.125, size * 0.875, size * 0.75]
    draw.rounded_rectangle(rect, radius=radius, fill=bubble_color)
    
    tail = [
        (size * 0.33, size * 0.75),
        (size * 0.5, size * 0.9),
        (size * 0.56, size * 0.75)
    ]
    draw.polygon(tail, fill=bubble_color)
    
    dot_radius = size / 14
    spacing = dot_radius * 2.5
    center_y = size * 0.45
    centers_x = [size / 2 - spacing, size / 2, size / 2 + spacing]
    
    for cx in centers_x:
        draw.ellipse(
            [(cx - dot_radius, center_y - dot_radius), (cx + dot_radius, center_y + dot_radius)],
            fill=dot_color
        )
    
    return image

# === Spotify Functions ===
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

spotify_cache = {
    "song": None,
    "artist": None,
    "duration_ms": 0,
    "last_progress_ms": 0,
    "last_fetch_time": 0,
    "is_playing": False
}

def fetch_spotify_playback(max_retries=3, delay=2):
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
                time.sleep(delay * attempt)
            else:
                return False

def get_spotify_message_with_progress_update(fetch_interval=15):
    now = time.time()
    time_since_fetch = now - spotify_cache["last_fetch_time"]

    if spotify_cache["is_playing"]:
        elapsed = time_since_fetch * 1000
        current_progress = int(spotify_cache["last_progress_ms"] + elapsed)

        if current_progress >= spotify_cache["duration_ms"]:
            success = fetch_spotify_playback()
            if not success:
                return "⏸️ Nothing playing"
        elif time_since_fetch > fetch_interval:
            success = fetch_spotify_playback()
            if not success:
                return "⏸️ Nothing playing"
    else:
        if time_since_fetch > fetch_interval:
            success = fetch_spotify_playback()
            if not success:
                return "⏸️ Nothing playing"

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

# === System Info ===
def get_system_stats():
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

# === OSC Send ===
def send_to_vrchat(msg):
    client.send_message(OSC_ADDRESS, [msg, True])
    print("Sent:\n" + msg + "\n" + "-"*30)

# === State and Thread Control ===
current_mode = "full"
current_mode_lock = threading.Lock()
stop_event = threading.Event()
last_message = ""

# === Main update loop ===
def update_loop():
    global last_message
    while not stop_event.is_set():
        with current_mode_lock:
            mode = current_mode

        system_info = get_system_stats()
        song_info = get_spotify_message_with_progress_update()

        if mode == "full":
            full_message = system_info + "\n\n" + (song_info or "⏸️ Nothing playing")
        elif mode == "system":
            full_message = system_info
        elif mode == "spotify":
            full_message = song_info or "⏸️ Nothing playing"
        else:
            full_message = "Unknown mode"

        if full_message != last_message:
            send_to_vrchat(full_message)
            last_message = full_message

        time.sleep(2)

# === Tray menu actions ===
def on_mode_change(icon, item):
    global current_mode
    with current_mode_lock:
        current_mode = item.text
    print(f"Mode changed to: {current_mode}")
    icon.menu = pystray.Menu(*create_menu())
    icon.update_menu()

def on_quit(icon, item):
    stop_event.set()
    icon.stop()

def create_menu():
    with current_mode_lock:
        mode = current_mode
    return (
        item("full", on_mode_change, checked=lambda item: item.text == mode, radio=True),
        item("system", on_mode_change, checked=lambda item: item.text == mode, radio=True),
        item("spotify", on_mode_change, checked=lambda item: item.text == mode, radio=True),
        item("Quit", on_quit)
    )

# === Main ===
if __name__ == "__main__":
    print("🚀 VRChat Tray Status App Started")
    icon_image = create_chat_bubble_icon(64)
    
    # Start background thread
    thread = threading.Thread(target=update_loop, daemon=True)
    thread.start()
    
    # Create and run tray icon
    icon = pystray.Icon("VRChatStatus", icon_image, "VRChat System + Spotify", pystray.Menu(*create_menu()))
    icon.run()
    
    # Graceful shutdown
    stop_event.set()
    thread.join()
    print("🛑 Exited cleanly.")
