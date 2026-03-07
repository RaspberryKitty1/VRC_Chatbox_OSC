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

# === Optional GPU stats ===
GPU_AVAILABLE = False
try:
    import pynvml
    pynvml.nvmlInit()
    GPU_AVAILABLE = True
except ModuleNotFoundError:
    print("[GPU] nvidia-ml-py not installed, GPU stats disabled.")
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

def truncate_field(text, max_chars):
    if not text:
        return ""
    return text if len(text) <= max_chars else text[:max_chars-1] + "…"

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

async def get_spotify_message_vrchat():
    with spotify_paused_lock:
        if spotify_paused:
            return ""

    now = time.time()
    if now - spotify_cache["last_fetch"] > 4:
        await fetch_spotify_playback_async()

    if spotify_cache["is_playing"]:
        elapsed = int(now - spotify_cache["last_fetch"])
        current_progress = min(spotify_cache["progress"] + elapsed, spotify_cache["duration"])
        # Return full text, no truncation
        return f"🎵 {spotify_cache['song']}\n👤 {spotify_cache['artist']}\n⌛ {format_time(current_progress)} / {format_time(spotify_cache['duration'])}"
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
ws_client_count = 0

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
        return
    ws_server_stop_event.clear()
    ws_server_thread = threading.Thread(target=start_ws_server, daemon=True)
    ws_server_thread.start()

def maybe_stop_ws_server():
    global ws_server_thread
    if not ws_server_running:
        return
    ws_server_stop_event.set()
    if ws_server_thread:
        ws_server_thread.join(timeout=5)
        ws_server_thread = None

def get_extension_message_vrchat(max_title=40, max_uploader=30):
    """Return media message with truncated title/uploader and full duration."""
    now = time.time()
    with extension_data_lock:
        if extension_data["title"] and now - extension_data["last_update"] < 10:
            title = truncate_field(extension_data["title"], max_title)
            uploader = truncate_field(extension_data["uploader"], max_uploader)
            duration = "LIVE" if extension_data["live"] else format_time(extension_data["duration"])
            
            return f"📺 {title}\n👤 {uploader}\n⌛ {format_time(extension_data['currentTime'])} / {duration}"
    return ""

# === VRChat Message Builder (144 chars) ===
def build_dynamic_vrchat_message(system_info, spotify_info, media_info, max_length=144):
    """
    Build VRChat-safe message:
    - Max 144 chars (including newlines)
    - Preserve system info fully
    - Preserve blank line after system info
    - Preserve duration line fully
    - Truncate only middle content if needed
    """
    system_lines = system_info.split("\n") if system_info else []
    content = media_info or spotify_info or ""
    content_lines = content.split("\n") if content else []

    if content_lines:
        # Add blank line after system info
        content_lines = [""] + content_lines

    # Separate duration line
    duration_line = content_lines[-1] if content_lines else ""
    middle_lines = content_lines[:-1]

    # Join middle lines with newline
    middle_text = "\n".join(middle_lines)

    # Compute total length with newlines
    reserved_len = sum(len(line) for line in system_lines) + len(system_lines)  # system lines + newlines
    reserved_len += len(duration_line) + 1  # duration line + newline
    reserved_len += len(middle_lines)  # middle newlines

    available_len = max_length - reserved_len
    if available_len < 0:
        available_len = 0

    # Truncate middle content if needed
    if len(middle_text) > available_len:
        middle_text = middle_text[:max(0, available_len-1)] + "…"

    # Rebuild final string
    final_message = "\n".join(system_lines)
    if middle_text:
        final_message += "\n" + middle_text
    if duration_line:
        final_message += "\n" + duration_line

    return final_message




# === Tray Icon & Menu ===
current_mode = "full"
current_mode_lock = threading.Lock()
last_message = ""

spotify_paused = False
paused = False
paused_lock = threading.Lock()

def create_chat_bubble_icon(size=64, mode="full", spotify_paused=False, sending_paused=False):
    image = Image.new("RGBA", (size, size), (0,0,0,0))
    draw = ImageDraw.Draw(image)
    color_map = {
        "full": (30, 144, 255, 255),
        "system": (138, 43, 226, 255),
        "spotify": (30, 215, 96, 255),
        "media": (255, 69, 0, 255),
        "paused": (169, 169, 169, 255),
        "spotify_paused": (255, 215, 0, 255)
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

def on_mode_change(icon, item):
    global current_mode
    with current_mode_lock:
        current_mode = item.text
        if current_mode in ("full", "media"):
            maybe_start_ws_server()
        else:
            maybe_stop_ws_server()
    icon.icon = create_chat_bubble_icon(64, "paused" if paused else current_mode, spotify_paused=spotify_paused, sending_paused=paused)
    refresh_tray_menu(icon)

def on_toggle_pause(icon, item):
    global paused
    with paused_lock:
        paused = not paused
    icon.icon = create_chat_bubble_icon(64, "paused" if paused else current_mode, spotify_paused=spotify_paused, sending_paused=paused)
    refresh_tray_menu(icon)

def on_toggle_spotify_pause(icon, item):
    global spotify_paused
    with spotify_paused_lock:
        spotify_paused = not spotify_paused
    icon.icon = create_chat_bubble_icon(64, "paused" if paused else current_mode, spotify_paused=spotify_paused, sending_paused=paused)
    refresh_tray_menu(icon)

def on_quit(icon, item):
    stop_event.set()
    maybe_stop_ws_server()
    icon.stop()

def create_menu():
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

def refresh_tray_menu(icon):
    try:
        icon.menu = pystray.Menu(*create_menu())
        icon.update_menu()
        icon.visible = False
        icon.visible = True
    except Exception as e:
        print(f"[Tray Icon Refresh Error] {e}")

# === Main Update Loop ===
async def update_loop_async():
    global last_message
    while not stop_event.is_set():
        with current_mode_lock:
            mode = current_mode

        system_info = get_system_stats()
        spotify_info = await get_spotify_message_vrchat()
        media_info = get_extension_message_vrchat()

        if mode == "full":
            full_message = build_dynamic_vrchat_message(system_info, spotify_info, media_info, max_length=144)
        elif mode == "system":
            full_message = system_info[:144]
        elif mode == "spotify":
            full_message = spotify_info[:144] or "⏸️ Nothing playing"
        elif mode == "media":
            full_message = media_info[:144] or "⏸️ No video detected"
        else:
            full_message = "Unknown mode"

        if full_message != last_message:
            send_to_vrchat(full_message)
            last_message = full_message

        await asyncio.sleep(2)

# === Main Entrypoint ===
if __name__ == "__main__":
    print("🚀 VRChat Tray Status App Started")
    stop_event = threading.Event()

    icon_image = create_chat_bubble_icon(64, current_mode, spotify_paused=spotify_paused, sending_paused=paused)
    if current_mode in ("full", "media"):
        maybe_start_ws_server()

    threading.Thread(target=lambda: asyncio.run(update_loop_async()), daemon=True).start()

    icon = pystray.Icon(
        "VRChatStatus",
        icon_image,
        "VRChat System + Spotify + Media",
        pystray.Menu(*create_menu())
    )
    icon.run()

    stop_event.set()
   
