from pythonosc.udp_client import SimpleUDPClient

# Set the IP and port for VRChat's OSC input (default is localhost and port 9000)
ip = "127.0.0.1"
port = 9000

# OSC address for sending a message to the local chatbox
osc_address = "/chatbox/input"

# The message to send
message = "Hello from Python!"

# Whether the message should be visible in the VRChat HUD (True = shows in-game chatbox)
show_in_chatbox = True

# Create an OSC client
client = SimpleUDPClient(ip, port)

# Send the message
client.send_message(osc_address, [message, show_in_chatbox])
print(f"Message sent to VRChat: {message}")
