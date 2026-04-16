import os
import tempfile
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import whisper
from google import genai
from google.genai import types
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
    
    # Initialize Gemini
    gemini_client = None
    system_instruction = (
        "You are a bank loan interviewer. Your goal is to assess the borrower's eligibility "
        "for a loan by asking relevant questions about their financial history, income, purpose "
        "of the loan, and repayment plan. Be professional, polite, and thorough. The user's input "
        "is a continuous live transcript of their speech."
    )

    llm_api_key = "AIzaSyBQrF61wV32rpPsGOMyXYGARnvxDNKIcbA"
    if llm_api_key:
        try:
            gemini_client = genai.Client(api_key=llm_api_key)
            print("Gemini client initialized successfully.")
        except Exception as e:
            print(f"Error initializing Gemini: {e}")
    else:
        print("Warning: API Key not set. LLM responses will be disabled.")
    
    # Let frontend know we're initializing the model on first connect
    await websocket.send_json({"text": "Initializing AI Model... Give it a moment."})
    local_model = await get_model()
    await websocket.send_json({"text": "Model Active! Listening to your audio..."})
    
    # We accumulate the incoming audio stream into a bytearray.
    # Because MediaRecorder sends WebM Opus chunks, the header is only present 
    # in the very first incoming chunk. Concatenating them reconstructs a valid WebM file.
    audio_buffer = bytearray()
    
    last_llm_prompt = ""
    last_llm_response = ""
    
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
                    
                    # Trigger LLM if we have enough new text ending in punctuation
                    if gemini_client and transcript_text != last_llm_prompt and transcript_text[-1] in ".?!":
                        try:
                            # Ask Gemini async
                            response = await gemini_client.aio.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=transcript_text,
                                config=types.GenerateContentConfig(
                                    system_instruction=system_instruction,
                                )
                            )
                            if response and response.text:
                                last_llm_response = response.text
                                last_llm_prompt = transcript_text
                                print(f"[LLM RESPONDED]: {last_llm_response[:50]}...")
                        except Exception as e:
                            print(f"LLM Error: {e}")
                    
                    # Send accumulated transcript back to frontend to display
                    display_text = f"User: {transcript_text}"
                    if last_llm_response:
                        display_text += f"\n\nInterviewer: {last_llm_response}"
                        
                    await websocket.send_json({"text": display_text})
                    
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
