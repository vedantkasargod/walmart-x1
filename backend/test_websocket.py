
import websocket
import threading
import time

# The WebSocket URL of your running FastAPI backend
WEBSOCKET_URL = "ws://127.0.0.1:8000/listen"
# The path to your sample audio file
AUDIO_FILE_PATH = "test_websocket.mp3" # Or .mp3

def on_message(ws, message):
    """This function is called when a message is received from the server."""
    print(f"<<< Received from server: {message}")

def on_error(ws, error):
    """This function is called when an error occurs."""
    print(f"--- WebSocket Error: {error} ---")

def on_close(ws, close_status_code, close_msg):
    """This function is called when the connection is closed."""
    print("--- WebSocket Connection Closed ---")

def on_open(ws):
    """This function is called when the connection is first opened."""
    print("--- WebSocket Connection Opened ---")
    
    def send_audio_data():
        print(f">>> Reading audio file: {AUDIO_FILE_PATH}")
        try:
            with open(AUDIO_FILE_PATH, "rb") as f:
                while True:
                    # Read the audio file in small chunks
                    data = f.read(1024)
                    if not data:
                        break
                    # Send the chunk over the WebSocket
                    ws.send(data, websocket.ABNF.OPCODE_BINARY)
                    print(f">>> Sent a chunk of {len(data)} bytes")
                    time.sleep(0.05) # Simulate real-time streaming
            
            print(">>> Finished sending audio file.")
            # Close the connection after sending is complete
            ws.close()
        except FileNotFoundError:
            print(f"ERROR: Test audio file not found at '{AUDIO_FILE_PATH}'. Please record one.")
            ws.close()
        except Exception as e:
            print(f"ERROR: An error occurred while sending audio: {e}")
            ws.close()

    # Start sending the audio data in a separate thread
    threading.Thread(target=send_audio_data).start()


if __name__ == "__main__":
    print("--- Starting WebSocket Test Client ---")
    # Enable detailed tracing to see exactly what's happening
    websocket.enableTrace(True)
    # Create and run the WebSocket client
    ws_app = websocket.WebSocketApp(
        WEBSOCKET_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws_app.run_forever()