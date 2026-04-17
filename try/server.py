"""
try/server.py
─────────────
Minimal faster-whisper test server.
Run from the project root with the backend venv active:

    python try/server.py

Then open try/index.html in your browser (or visit http://localhost:8001).
"""

import os, tempfile, asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel
from starlette.websockets import WebSocketState

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Model (lazy-loaded on first connection) ──────────────────────────────────
_model: WhisperModel | None = None
_loading = False

async def get_model() -> WhisperModel:
    global _model, _loading
    if _model:
        return _model
    if _loading:
        while _model is None:
            await asyncio.sleep(0.3)
        return _model
    _loading = True
    print("\n[Whisper] Loading 'base' model with int8 quantization …")
    _model = await asyncio.to_thread(WhisperModel, "base", device="cpu", compute_type="int8")
    print("[Whisper] Model ready!\n")
    _loading = False
    return _model


# ── Serve the HTML UI ────────────────────────────────────────────────────────
@app.get("/")
async def index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "index.html"))


# ── WebSocket: receive audio chunks, return live transcript ─────────────────
@app.websocket("/ws")
async def ws_audio(websocket: WebSocket):
    await websocket.accept()
    print("[WS] Client connected")

    await websocket.send_json({"type": "status", "text": "Loading Whisper model…"})
    model = await get_model()
    await websocket.send_json({"type": "status", "text": "Ready — start speaking!"})

    audio_buf  = bytearray()
    last_text  = ""
    MAX_BYTES  = 2 * 1024 * 1024   # 2 MB rolling window (~60 s of webm)
    tmp_path   = None

    async def safe_send(data: dict):
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(data)
        except Exception:
            pass

    try:
        while True:
            msg = await websocket.receive()

            if "bytes" not in msg:
                continue

            audio_buf.extend(msg["bytes"])

            # Roll the buffer to prevent ever-growing transcription time
            if len(audio_buf) > MAX_BYTES:
                audio_buf = audio_buf[-MAX_BYTES:]

            # Write to a temp file and transcribe
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
                f.write(audio_buf)
                tmp_path = f.name

            try:
                segments, info = await asyncio.to_thread(
                    model.transcribe,
                    tmp_path,
                    beam_size=1,
                    language="en",
                    vad_filter=True,        # skip silence
                    vad_parameters={"min_silence_duration_ms": 500},
                )
                text = " ".join(s.text for s in segments).strip()

                if text and text != last_text:
                    last_text = text
                    word_count = len(text.split())
                    await safe_send({
                        "type":       "transcript",
                        "text":       text,
                        "lang":       info.language,
                        "lang_prob":  round(info.language_probability, 3),
                        "words":      word_count,
                        "duration":   round(info.duration, 2),
                    })

            except Exception as e:
                print(f"[Whisper] Transcription error: {e}")
                await safe_send({"type": "error", "text": str(e)})
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)
                    tmp_path = None

    except WebSocketDisconnect:
        print("[WS] Client disconnected")
    except Exception as e:
        print(f"[WS] Error: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8001, reload=True,
                reload_dirs=[os.path.dirname(__file__)])
