# === Imports and Setup ===
import asyncio
import json
import os
import threading
import time
from datetime import datetime

import psutil
import pystray
import spotipy
import websockets
from dotenv import load_dotenv
from PIL import Image, ImageDraw
from pystray import MenuItem as item
from pythonosc.udp_client import SimpleUDPClient
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError
from requests.exceptions import RequestException
from websockets.exceptions import ConnectionClosedError
from json import JSONDecodeError

# === Optional GPU stats ===
try:
    import pynvml
    pynvml.nvmlInit()
    gpu_available = True
except (ModuleNotFoundError, pynvml.NVMLError):
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

    color_map = {
        "full": (30, 144, 255, 255),
        "system": (169, 169, 169, 255),
        "spotify": (30, 215, 96, 255),
        "media": (255, 69, 0, 255)
    }
    bubble_color = color_map.get(mode, (100, 100, 100, 255))
    dot_color = (255, 255, 255, 255)

    radius = size // 6
    rect = [size * 0.125, size * 0.125, size * 0.875, size * 0.75]
    draw.rounded_rectangle(rect, radius=radius, fill=bubble_color)

    tail = [(size * 0.33, size * 0.75), (size * 0.5, size * 0.9), (size * 0.56, size * 0.75)]
    draw.polygon(tail, fill=bubble_color)

    dot_radius = size / 14
    spacing = dot_radius * 2.5
    center_y = size * 0.45
    centers_x = [size / 2 - spacing, size / 2, size / 2 + spacing]
    for cx in centers_x:
        draw.ellipse([(cx - dot_radius, center_y - dot_radius), (cx + dot_radius, center_y + dot_radius)], fill=dot_color)

    return image

# === Helper: shorten long titles ===
def shorten_title(title, max_length=60):
    return title if len(title) <= max_length else title[:max_length - 1] + "…"

# === Spotify Functions ===
def get_spotify_client():
    try:
        token_info = auth_manager.get_cached_token()
        if not token_info:
            token_info = auth_manager.get_access_token()
        if auth_manager.is_token_expired(token_info):
            token_info = auth_manager.refresh_access_token(token_info['refresh_token'])
        return spotipy.Spotify(auth=token_info['access_token'])
    except SpotifyOauthError as e:
        try:
            auth_url = auth_manager.get_authorize_url()
            print("Open the URL manually to authenticate:\n" + auth_url)
        except SpotifyOauthError as auth_url_error:
            print(f"[Spotify Auth URL Error] {auth_url_error}")
        return None
    except Exception as e:
        print(f"[Spotify Client Error] {e}")
        return None


def format_time(seconds):
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, secs = divmod(seconds, 60)
    if days:
        return f"{days}:{hours:02}:{minutes:02}:{secs:02}"
    elif hours:
        return f"{hours}:{minutes:02}:{secs:02}"
    else:
        return f"{minutes}:{secs:02}"


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
            if current and current.get("is_playing") and current["item"]:
                track = current["item"]
                spotify_cache.update({
                    "song": track["name"],
                    "artist": ", ".join(a["name"] for a in track["artists"]),
                    "duration_ms": track["duration_ms"] // 1000,
                    "last_progress_ms": current["progress_ms"] // 1000,
                    "last_fetch_time": time.time(),
                    "is_playing": True,
                    "last_stopped_time": 0
                })
                return True
            else:
                now = time.time()
                if spotify_cache["is_playing"]:
                    spotify_cache["last_stopped_time"] = now
                spotify_cache["is_playing"] = False
                spotify_cache["last_fetch_time"] = now
                return False
        except SpotifyException as e:
            print(f"[Spotify API Error] {e}")
        except RequestException as e:
            print(f"[Spotify Network Error] {e}")
        except Exception as e:
            print(f"[Spotify Unexpected Error] {e}")
        if attempt < max_retries:
            time.sleep(delay * attempt)
    return False


def get_spotify_message_with_progress_update(fetch_interval=15):
    now = time.time()
    if now - spotify_cache["last_fetch_time"] > fetch_interval:
        fetch_spotify_playback()

    if spotify_cache["is_playing"]:
        elapsed = now - spotify_cache["last_fetch_time"]
        current_progress = min(spotify_cache["last_progress_ms"] + int(elapsed), spotify_cache["duration_ms"])

        return f"🎵 {shorten_title(spotify_cache['song'])}\n👤 {shorten_title(spotify_cache['artist'])}\n⌛ {format_time(current_progress)} / {format_time(spotify_cache['duration_ms'])}"
    elif spotify_cache["last_stopped_time"] and (now - spotify_cache["last_stopped_time"] < 10):
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
            gpu = "Err"
            print(f"[GPU Stat Error] {e}")

    return f"{now}\nCPU:{cpu:.0f}% | GPU:{gpu} | RAM:{ram:.0f}%"

# === OSC Send ===
def send_to_vrchat(msg):
    try:
        client.send_message(OSC_ADDRESS, [msg, True])
        print("Sent:\n" + msg + "\n" + "-" * 30)
    except Exception as e:
        print(f"[OSC Send Error] {e}")

# === Extension WebSocket Shared State ===
extension_data = {
    "title": None,
    "uploader": "",
    "duration": 0,
    "currentTime": 0,
    "last_update": 0,
    "live": False
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
            try:
                data = json.loads(message)
                with extension_data_lock:
                    extension_data.update({
                        "title": data.get("title"),
                        "uploader": data.get("streamer") or data.get("uploader") or "",
                        "duration": data.get("duration", 0),
                        "currentTime": data.get("currentTime", 0),
                        "last_update": time.time(),
                        "live": data.get("live", False)
                    })
            except JSONDecodeError as e:
                print(f"[WebSocket JSON Error] {e}")
    except ConnectionClosedError as e:
        print(f"[WebSocket Closed] {e}")
    except Exception as e:
        print(f"[WebSocket Error] {e}")
    finally:
        print("[WebSocket] Client disconnected.")


def start_ws_server():
    global ws_server_running
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def run_server():
        global ws_server_running
        try:
            async with websockets.serve(ws_handler, "localhost", 12345):
                ws_server_running = True
                print("[WebSocket] Server started on ws://localhost:12345")
                while not ws_server_stop_event.is_set():
                    await asyncio.sleep(1)
                print("[WebSocket] Server stopping...")
        except OSError as e:
            print(f"[WebSocket Server Error] {e}")

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
            parts = [f"📺 {shorten_title(extension_data['title'])}"]
            if extension_data["uploader"]:
                parts.append(f"👤 {extension_data['uploader']}")
            duration = "LIVE" if extension_data["live"] else format_time(extension_data["duration"])
            parts.append(f"⌛ {format_time(extension_data['currentTime'])} / {duration}")
            return "\n".join(parts)
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
        elif mode == "media":
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
        if current_mode in ("full", "media"):
            maybe_start_ws_server()
        else:
            maybe_stop_ws_server()

    icon.icon = create_chat_bubble_icon(64, current_mode)
    try:
        icon.menu = pystray.Menu(*create_menu())
        icon.update_menu()
        icon.visible = False
        icon.visible = True
    except Exception as e:
        print(f"[Tray Icon Refresh Error] {e}")


def on_quit(icon, item):
    stop_event.set()
    maybe_stop_ws_server()
    icon.stop()


def create_menu():
    with current_mode_lock:
        mode = current_mode
    return (
        item("full", on_mode_change, checked=lambda i: i.text == mode, radio=True),
        item("system", on_mode_change, checked=lambda i: i.text == mode, radio=True),
        item("spotify", on_mode_change, checked=lambda i: i.text == mode, radio=True),
        item("media", on_mode_change, checked=lambda i: i.text == mode, radio=True),
        item("Quit", on_quit)
    )

# === Main ===
if __name__ == "__main__":
    print("🚀 VRChat Tray Status App Started")
    icon_image = create_chat_bubble_icon(64, current_mode)

    if current_mode in ("full", "media"):
        maybe_start_ws_server()

    thread = threading.Thread(target=update_loop, daemon=True)
    thread.start()

    icon = pystray.Icon("VRChatStatus", icon_image,
                        "VRChat System + Spotify + Media", pystray.Menu(*create_menu()))
    icon.run()

    stop_event.set()
    maybe_stop_ws_server()
    thread.join()
    print("🛑 Exited cleanly.")
