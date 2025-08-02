import asyncio
import json
import os
import threading
import time
from datetime import datetime

import psutil
import pystray
import requests
import spotipy
import websockets
from dotenv import load_dotenv
from PIL import Image, ImageDraw
from pystray import MenuItem as item
from pythonosc.udp_client import SimpleUDPClient
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError

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

VRCHAT_IP = os.getenv("VRCHAT_IP")
VRCHAT_PORT = 9000
OSC_ADDRESS = "/chatbox/input"
client = SimpleUDPClient(VRCHAT_IP, VRCHAT_PORT)

# === Spotify Auth Setup ===
auth_manager = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope="user-read-playback-state",
    cache_path=".spotify_token_cache"
)

# === Tray icon creator ===
def create_chat_bubble_icon(size=64, mode="full"):
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    if mode == "full":
        bubble_color = (30, 144, 255, 255)  # Blue
    elif mode == "system":
        bubble_color = (169, 169, 169, 255)  # Gray
    elif mode == "spotify":
        bubble_color = (30, 215, 96, 255)  # Spotify green
    elif mode == "youtube":
        bubble_color = (255, 69, 0, 255)  # Orange Red for YouTube
    else:
        bubble_color = (100, 100, 100, 255)
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
            [(cx - dot_radius, center_y - dot_radius),
             (cx + dot_radius, center_y + dot_radius)],
            fill=dot_color
        )
    return image

# === Spotify Functions ===
def get_spotify_client():
    token_info = auth_manager.get_cached_token()
    if not token_info:
        print("[Spotify Auth] No cached token found. Attempting to get access token...")
        try:
            token_info = auth_manager.get_access_token()
        except SpotifyOauthError as e:
            print(f"[Spotify Auth Error] Failed to get access token: {e}")
            try:
                auth_url = auth_manager.get_authorize_url()
                print("If the browser didn't open, visit this URL manually:\n" + auth_url)
            except SpotifyOauthError:
                print("Could not generate auth URL.")
            return None
        if not token_info:
            print("[Spotify Auth] Token still missing after auth attempt.")
            return None
    if auth_manager.is_token_expired(token_info):
        try:
            token_info = auth_manager.refresh_access_token(token_info['refresh_token'])
        except SpotifyOauthError as e:
            print(f"[Spotify Refresh Error] {e}")
            return None
    return spotipy.Spotify(auth=token_info['access_token'])

def format_time(seconds):
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes}:{str(secs).zfill(2)}"

spotify_cache = {
    "song": None,
    "artist": None,
    "duration_ms": 0,
    "last_progress_ms": 0,
    "last_fetch_time": 0,
    "is_playing": False,
    "last_stopped_time": 0  
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
                spotify_cache["duration_ms"] = track["duration_ms"] // 1000
                spotify_cache["last_progress_ms"] = current["progress_ms"] // 1000
                spotify_cache["last_fetch_time"] = time.time()
                spotify_cache["is_playing"] = True
                spotify_cache["last_stopped_time"] = 0
                return True
            else:
                now = time.time()
                if spotify_cache["is_playing"]:
                    spotify_cache["last_stopped_time"] = now
                spotify_cache["is_playing"] = False
                spotify_cache["last_fetch_time"] = now
                return False
        except (SpotifyException, requests.exceptions.RequestException, KeyError, AttributeError) as e:
            print(f"[Attempt {attempt}/{max_retries}] Spotify Fetch Error: {e}")
            if attempt < max_retries:
                time.sleep(delay * attempt)
            else:
                return False

def get_spotify_message_with_progress_update(fetch_interval=15):
    now = time.time()
    time_since_fetch = now - spotify_cache["last_fetch_time"]

    if time_since_fetch > fetch_interval:
        fetch_spotify_playback()

    if spotify_cache["is_playing"]:
        elapsed = now - spotify_cache["last_fetch_time"]
        current_progress = spotify_cache["last_progress_ms"] + int(elapsed)
        if current_progress > spotify_cache["duration_ms"]:
            current_progress = spotify_cache["duration_ms"]

        progress_str = format_time(current_progress)
        duration_str = format_time(spotify_cache["duration_ms"])
        return f"🎵 {spotify_cache['song']} by {spotify_cache['artist']}\n{progress_str} / {duration_str}"
    else:
        if spotify_cache["last_stopped_time"] and (now - spotify_cache["last_stopped_time"] < 10):
            return "⏸️ Nothing playing"
        else:
            return ""

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
        except pynvml.NVMLError as e:
            print(f"[GPU Error] {e}")
            gpu = "Err"

    return f"{now}\nCPU:{cpu:.0f}% | GPU:{gpu} | RAM:{ram:.0f}%"

# === OSC Send ===
def send_to_vrchat(msg):
    client.send_message(OSC_ADDRESS, [msg, True])
    print("Sent:\n" + msg + "\n" + "-"*30)

# === Extension WebSocket Shared State ===
extension_data = {
    "title": None,
    "duration": 0,
    "currentTime": 0,
    "last_update": 0
}
extension_data_lock = threading.Lock()

# === WebSocket Server State ===
ws_server_thread = None
ws_server_running = False
ws_server_stop_event = threading.Event()

# === WebSocket Server Handler ===
async def ws_handler(websocket, path):
    print("[WebSocket] Client connected.")
    try:
        async for message in websocket:
            data = json.loads(message)
            with extension_data_lock:
                extension_data.update({
                    "title": data.get("title"),
                    "duration": data.get("duration", 0),
                    "currentTime": data.get("currentTime", 0),
                    "last_update": time.time()
                })
    except Exception as e:
        print(f"[WebSocket] Error: {e}")
    finally:
        print("[WebSocket] Client disconnected.")

def start_ws_server():
    global ws_server_running
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def run_server():
        global ws_server_running
        async with websockets.serve(ws_handler, "localhost", 12345):
            ws_server_running = True
            print("[WebSocket] Server started on ws://localhost:12345")
            while not ws_server_stop_event.is_set():
                await asyncio.sleep(1)
            print("[WebSocket] Server stopping...")

    loop.run_until_complete(run_server())
    ws_server_running = False

def maybe_start_ws_server():
    global ws_server_thread
    if not ws_server_running:
        ws_server_stop_event.clear()
        ws_server_thread = threading.Thread(target=start_ws_server, daemon=True)
        ws_server_thread.start()

def maybe_stop_ws_server():
    global ws_server_thread
    if ws_server_running:
        ws_server_stop_event.set()
        if ws_server_thread:
            ws_server_thread.join(timeout=5)
            ws_server_thread = None

# === Extension Info Formatting ===
def get_extension_message():
    now = time.time()
    with extension_data_lock:
        if extension_data["title"] and (now - extension_data["last_update"] < 10):
            title = extension_data["title"]
            curr = format_time(extension_data["currentTime"])
            dur = format_time(extension_data["duration"])
            return f"📺 {title}\n{curr} / {dur}"
    return ""

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
        ext_info = get_extension_message()

        if mode == "full":
            parts = [system_info]
            if ext_info:
                parts.append(ext_info)
            elif song_info:
                parts.append(song_info)
            full_message = "\n\n".join(parts)
        elif mode == "system":
            full_message = system_info
        elif mode == "spotify":
            full_message = song_info or "⏸️ Nothing playing"
        elif mode == "youtube":
            full_message = ext_info or "⏸️ No video detected"
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
        if current_mode in ("full", "youtube"):
            maybe_start_ws_server()
        else:
            maybe_stop_ws_server()

    icon.icon = create_chat_bubble_icon(64, current_mode)
    icon.menu = pystray.Menu(*create_menu())
    icon.update_menu()
    icon.visible = False
    icon.visible = True

def on_quit(icon, item):
    stop_event.set()
    maybe_stop_ws_server()
    icon.stop()

def create_menu():
    with current_mode_lock:
        mode = current_mode
    return (
        item("full", on_mode_change,
             checked=lambda item: item.text == mode, radio=True),
        item("system", on_mode_change,
             checked=lambda item: item.text == mode, radio=True),
        item("spotify", on_mode_change,
             checked=lambda item: item.text == mode, radio=True),
        item("youtube", on_mode_change,
             checked=lambda item: item.text == mode, radio=True),
        item("Quit", on_quit)
    )

# === Main ===
if __name__ == "__main__":
    print("🚀 VRChat Tray Status App Started")
    icon_image = create_chat_bubble_icon(64, current_mode)

    if current_mode in ("full", "youtube"):
        maybe_start_ws_server()

    thread = threading.Thread(target=update_loop, daemon=True)
    thread.start()

    icon = pystray.Icon("VRChatStatus", icon_image, "VRChat System + Spotify + YouTube", pystray.Menu(*create_menu()))
    icon.run()

    stop_event.set()
    maybe_stop_ws_server()
    thread.join()
    print("🛑 Exited cleanly.")
