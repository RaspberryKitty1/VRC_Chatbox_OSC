# === Standard Library Imports ===
import asyncio
import json
import os
import threading
import time
from datetime import datetime

# === Third-Party Imports ===
import psutil
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError
from spotipy.exceptions import SpotifyException
from requests.exceptions import RequestException
from pythonosc.udp_client import SimpleUDPClient
import websockets
from websockets.exceptions import ConnectionClosedError


# === Optional GPU stats (run only at startup) ===
GPU_AVAILABLE = False
try:
    import pynvml
    pynvml.nvmlInit()
    GPU_AVAILABLE = True
except ModuleNotFoundError:
    print("[GPU] pynvml not installed, GPU stats disabled.")
except pynvml.NVMLError as e:
    print(f"[GPU] NVML initialization failed: {e}, GPU stats disabled.")


# === Load Environment Variables ===
load_dotenv()
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")
VRCHAT_IP = os.getenv("VRCHAT_IP")
VRCHAT_PORT = 9000
OSC_ADDRESS = "/chatbox/input"

# === Utility Functions ===
def shorten_title(title, max_length=50):
    return title if len(title) <= max_length else title[:max_length - 1] + "…"

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

# === Spotify Module ===
auth_manager = SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope="user-read-playback-state",
    cache_path=".spotify_token_cache"
)

spotify_client = None
spotify_client_lock = threading.Lock()
spotify_paused = False
spotify_paused_lock = threading.Lock()
spotify_cache = {
    "song": None, "artist": None, "duration": 0,
    "progress": 0, "last_fetch": 0, "is_playing": False, "last_stopped": 0
}

def get_spotify_client():
    global spotify_client
    with spotify_client_lock:
        try:
            token_info = auth_manager.get_cached_token()
            if not token_info:
                token_info = auth_manager.get_access_token()
            elif auth_manager.is_token_expired(token_info):
                token_info = auth_manager.refresh_access_token(token_info['refresh_token'])

            if spotify_client is None:
                spotify_client = spotipy.Spotify(auth=token_info['access_token'])
            else:
                spotify_client._auth = token_info['access_token']
            return spotify_client
        except SpotifyOauthError:
            print("[Spotify Auth Error] Re-authenticate via URL:")
            print(auth_manager.get_authorize_url())
        except Exception as e:
            print(f"[Spotify Client Error] {e}")
            spotify_client = None
    return None

async def fetch_spotify_playback_async(max_retries=3, delay=2):
    with spotify_paused_lock:
        if spotify_paused: return False

    for attempt in range(max_retries):
        try:
            client = get_spotify_client()
            if not client: return False
            loop = asyncio.get_event_loop()
            current = await loop.run_in_executor(None, client.current_playback)
            now = time.time()

            if current and current.get("is_playing") and current.get("item"):
                track = current["item"]
                spotify_cache.update({
                    "song": track["name"],
                    "artist": ", ".join(a["name"] for a in track["artists"]),
                    "duration": track["duration_ms"] // 1000,
                    "progress": current["progress_ms"] // 1000,
                    "last_fetch": now,
                    "is_playing": True,
                    "last_stopped": 0
                })
                return True
            else:
                if spotify_cache["is_playing"]:
                    spotify_cache["last_stopped"] = now
                spotify_cache["is_playing"] = False
                spotify_cache["last_fetch"] = now
                return False
        except (SpotifyException, RequestException) as e:
            print(f"[Spotify API/Network Error] {e}")
        except Exception as e:
            print(f"[Spotify Unexpected Error] {e}")
        await asyncio.sleep(delay * (attempt + 1))
    return False

async def get_spotify_message_async(fetch_interval=15):
    with spotify_paused_lock:
        if spotify_paused: return ""
    now = time.time()
    if now - spotify_cache["last_fetch"] > fetch_interval:
        await fetch_spotify_playback_async()
    if spotify_cache["is_playing"]:
        elapsed = int(now - spotify_cache["last_fetch"])
        current_progress = min(spotify_cache["progress"] + elapsed, spotify_cache["duration"])
        return f"🎵 {shorten_title(spotify_cache['song'])}\n👤 {shorten_title(spotify_cache['artist'])}\n⌛ {format_time(current_progress)} / {format_time(spotify_cache['duration'])}"
    elif spotify_cache["last_stopped"] and (now - spotify_cache["last_stopped"] < 10):
        return "⏸️ Nothing playing"
    return ""

# === VRChat OSC Module ===
osc_client = SimpleUDPClient(VRCHAT_IP, VRCHAT_PORT)
paused = False
paused_lock = threading.Lock()

def send_to_vrchat(msg):
    with paused_lock:
        if paused: return
    try:
        osc_client.send_message(OSC_ADDRESS, [msg, True])
        print("Sent:\n" + msg + "\n" + "-"*30)
    except Exception as e:
        print(f"[OSC Send Error] {e}")

# === System Stats Module ===
def get_system_stats():
    now = datetime.now().strftime("🕒 %I:%M %p")
    cpu = round(psutil.cpu_percent())
    ram = round(psutil.virtual_memory().percent)
    gpu = "N/A"

    if GPU_AVAILABLE:
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            gpu = round(util.gpu)
        except pynvml.NVMLError as e:
            gpu = "Err"
            print(f"[GPU Stat Error] {e}")

    return f"{now}\nCPU:{cpu}% | GPU:{gpu}% | RAM:{ram}%"


# === WebSocket Extension Module ===
extension_data = {"title": None, "uploader": "", "duration":0, "currentTime":0, "last_update":0, "live":False}
extension_data_lock = threading.Lock()
ws_server_thread = None
ws_server_running = False
ws_server_stop_event = threading.Event()
ws_client_count = 0  # optional: track active clients

async def ws_handler(websocket, path):
    global ws_client_count
    ws_client_count += 1
    print(f"[WebSocket] Client connected. Total clients: {ws_client_count}")
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
            except json.JSONDecodeError as e:
                print(f"[WebSocket JSON Error] {e}")
    except ConnectionClosedError:
        print("[WebSocket] Connection closed by client.")
    finally:
        ws_client_count -= 1
        print(f"[WebSocket] Client disconnected. Total clients: {ws_client_count}")


def start_ws_server():
    global ws_server_running
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def run_server():
        global ws_server_running
        print("[WebSocket] Server starting on ws://localhost:12345...")
        async with websockets.serve(ws_handler, "localhost", 12345):
            ws_server_running = True
            print("[WebSocket] Server running.")
            while not ws_server_stop_event.is_set():
                await asyncio.sleep(1)
        ws_server_running = False
        print("[WebSocket] Server stopped.")

    loop.run_until_complete(run_server())


def maybe_start_ws_server():
    global ws_server_thread
    if ws_server_running:
        print("[WebSocket] Server already running.")
        return
    print("[WebSocket] Starting server thread...")
    ws_server_stop_event.clear()
    ws_server_thread = threading.Thread(target=start_ws_server, daemon=True)
    ws_server_thread.start()


def maybe_stop_ws_server():
    global ws_server_thread
    if not ws_server_running:
        print("[WebSocket] Server not running.")
        return
    print("[WebSocket] Stopping server...")
    ws_server_stop_event.set()
    if ws_server_thread:
        ws_server_thread.join(timeout=5)
        ws_server_thread = None
    print("[WebSocket] Server stop signal sent.")


def get_extension_message():
    now = time.time()
    with extension_data_lock:
        if extension_data["title"] and now - extension_data["last_update"] < 10:
            parts = [f"📺 {shorten_title(extension_data['title'])}"]
            if extension_data["uploader"]:
                parts.append(f"👤 {extension_data['uploader']}")
            duration = "LIVE" if extension_data["live"] else format_time(extension_data["duration"])
            parts.append(f"⌛ {format_time(extension_data['currentTime'])} / {duration}")
            return "\n".join(parts)
    return ""


# === Tray Icon & Menu ===
current_mode = "full"
current_mode_lock = threading.Lock()
last_message = ""

def create_chat_bubble_icon(size=64, mode="full", spotify_paused=False, sending_paused=False):
    image = Image.new("RGBA", (size, size), (0,0,0,0))
    draw = ImageDraw.Draw(image)
    color_map = {
    "full": (30, 144, 255, 255),       # Dodger Blue
    "system": (138, 43, 226, 255),     # BlueViolet (distinct purple)
    "spotify": (30, 215, 96, 255),     # Spotify green
    "media": (255, 69, 0, 255),        # OrangeRed
    "paused": (169, 169, 169, 255),    # DarkGray for paused
    "spotify_paused": (255, 215, 0, 255) # Gold
}


    if sending_paused:
        bubble_color = color_map["paused"]
    elif spotify_paused:
        bubble_color = color_map["spotify_paused"]
    else:
        bubble_color = color_map.get(mode, (100,100,100,255))
    dot_color = (255,255,255,255)
    radius = size//6
    rect = [size*0.125, size*0.125, size*0.875, size*0.75]
    draw.rounded_rectangle(rect, radius=radius, fill=bubble_color)
    tail = [(size*0.33, size*0.75),(size*0.5, size*0.9),(size*0.56, size*0.75)]
    draw.polygon(tail, fill=bubble_color)
    dot_radius = size/14
    spacing = dot_radius*2.5
    center_y = size*0.45
    centers_x = [size/2 - spacing, size/2, size/2 + spacing]
    for cx in centers_x:
        draw.ellipse([(cx-dot_radius, center_y-dot_radius),(cx+dot_radius, center_y+dot_radius)], fill=dot_color)
    return image

# === Main Update Loop ===
async def update_loop_async():
    global last_message
    while not stop_event.is_set():
        with current_mode_lock:
            mode = current_mode

        system_info = get_system_stats()
        ext_info = get_extension_message()
        song_info = await get_spotify_message_async()

        if mode == "full":
            parts = [system_info]
            if ext_info: parts.append(ext_info)
            elif song_info: parts.append(song_info)
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

        await asyncio.sleep(2)
        
# === Tray menu actions ===
def on_mode_change(icon, item):
    global current_mode
    with current_mode_lock:
        current_mode = item.text
        print(f"[Tray] Mode changed to: {current_mode}")
        if current_mode in ("full", "media"):
            maybe_start_ws_server()
        else:
            maybe_stop_ws_server()

    icon.icon = create_chat_bubble_icon(
        64,
        "paused" if paused else current_mode,
        spotify_paused=spotify_paused,
        sending_paused=paused
    )
    refresh_tray_menu(icon)


def on_toggle_pause(icon, item):
    global paused
    with paused_lock:
        paused = not paused
    state = "Paused" if paused else "Resumed"
    print(f"🟡 Message sending {state}.")
    icon.icon = create_chat_bubble_icon(
        64,
        "paused" if paused else current_mode,
        spotify_paused=spotify_paused,
        sending_paused=paused
    )
    refresh_tray_menu(icon)


def on_toggle_spotify_pause(icon, item):
    global spotify_paused
    with spotify_paused_lock:
        spotify_paused = not spotify_paused
    state = "Paused" if spotify_paused else "Resumed"
    print(f"🟢 Spotify fetching {state}.")
    icon.icon = create_chat_bubble_icon(
        64,
        "paused" if paused else current_mode,
        spotify_paused=spotify_paused,
        sending_paused=paused
    )
    refresh_tray_menu(icon)


def on_quit(icon, item):
    stop_event.set()
    maybe_stop_ws_server()
    icon.stop()
    print("🛑 Exited cleanly.")


def refresh_tray_menu(icon):
    """Rebuild the menu dynamically to reflect current states."""
    try:
        icon.menu = pystray.Menu(*create_menu())
        icon.update_menu()
        # Force refresh
        icon.visible = False
        icon.visible = True
    except Exception as e:
        print(f"[Tray Icon Refresh Error] {e}")


def create_menu():
    """Return a tuple of MenuItems with checkmarks and dynamic text."""
    with current_mode_lock:
        mode = current_mode
    with paused_lock:
        is_paused = paused
    with spotify_paused_lock:
        is_spotify_paused = spotify_paused

    return (
        item("full", on_mode_change, checked=lambda i: i.text == mode, radio=True),
        item("system", on_mode_change, checked=lambda i: i.text == mode, radio=True),
        item("spotify", on_mode_change, checked=lambda i: i.text == mode, radio=True),
        item("media", on_mode_change, checked=lambda i: i.text == mode, radio=True),
        item("────────────", lambda: None, enabled=False),
        item("Pause Sending" if not is_paused else "Resume Sending", on_toggle_pause),
        item("Pause Spotify" if not is_spotify_paused else "Resume Spotify", on_toggle_spotify_pause),
        item("Quit", on_quit)
    )


# === Main Entrypoint ===
if __name__ == "__main__":
    print("🚀 VRChat Tray Status App Started")
    stop_event = threading.Event()

    # Initial tray icon
    icon_image = create_chat_bubble_icon(64, current_mode, spotify_paused=spotify_paused, sending_paused=paused)

    if current_mode in ("full", "media"):
        maybe_start_ws_server()

    # Start async update loop
    threading.Thread(target=lambda: asyncio.run(update_loop_async()), daemon=True).start()

    # Start tray icon
    icon = pystray.Icon(
        "VRChatStatus",
        icon_image,
        "VRChat System + Spotify + Media",
        pystray.Menu(*create_menu())
    )
    icon.run()

    stop_event.set()
    maybe_stop_ws_server()
