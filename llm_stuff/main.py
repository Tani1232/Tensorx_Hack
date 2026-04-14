import os
import tempfile
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import whisper

app = FastAPI()

# We will lazy-load the model to prevent uvicorn from hanging on startup
model = None
is_loading = False

async def get_model():
    global model, is_loading
    if model is None:
        if is_loading:
            # Wait if another request is currently loading the model
            while model is None:
                await asyncio.sleep(0.5)
            return model
            
        is_loading = True
        print("\n--- Lazy Loading Whisper 'base' Model ---")
        print("Downloading/Loading into memory... This may take a few minutes if downloading ~140MB for the first time.")
        # Load in a background thread to prevent blocking FastAPI's event loop
        model = await asyncio.to_thread(whisper.load_model, "base")
        print("--- Whisper Model Loaded Successfully ---\n")
        is_loading = False
    return model

@app.get("/")
async def get_index():
    # Serve the index.html file for the frontend
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.websocket("/ws/audio")
async def audio_websocket(websocket: WebSocket):
    await websocket.accept()
    print("New WebSocket connection established.")
    
    # Let frontend know we're initializing the model on first connect
    await websocket.send_json({"text": "Initializing AI Model... Give it a moment."})
    local_model = await get_model()
    await websocket.send_json({"text": "Model Active! Listening to your audio..."})
    
    # We accumulate the incoming audio stream into a bytearray.
    # Because MediaRecorder sends WebM Opus chunks, the header is only present 
    # in the very first incoming chunk. Concatenating them reconstructs a valid WebM file.
    audio_buffer = bytearray()
    
    try:
        while True:
            # Receive binary chunks sent by frontend every 1s
            data = await websocket.receive_bytes()
            audio_buffer.extend(data)
            
            # Write accumulated audio buffer to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
                tmp.write(audio_buffer)
                tmp_path = tmp.name
                
            try:
                # Run Whisper on the temporary file in a background thread
                result = await asyncio.to_thread(local_model.transcribe, tmp_path, fp16=False)
                transcript_text = result.get("text", "").strip()
                
                if transcript_text:
                    print(f"[TRANSCRIBED]: {transcript_text}")
                    # Send accumulated transcript back to frontend to display
                    await websocket.send_json({"text": transcript_text})
                    
            except Exception as e:
                print(f"Transcription Execution Error: {e}")
            finally:
                # Clean up the temporary file
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                    
    except WebSocketDisconnect:
        print("WebSocket client disconnected.")
    except Exception as e:
        print(f"WebSocket Error: {e}")

# Note: this file can be run via `uvicorn main:app --reload`
