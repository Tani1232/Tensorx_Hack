"""
app/websocket.py
----------------
WebSocket endpoint for real-time loan interview processing.

Key change from previous version:
  OLD: Accumulate audio buffer → upload full buffer to AssemblyAI REST
       every 350ms → wait 2-5s for response → pipeline stacks up.

  NEW: Open ONE AssemblyAI real-time WebSocket per session → stream
       raw audio chunks directly → receive partial transcripts in ~300ms
       as the person speaks. No upload, no polling, no buffer re-reads.

AssemblyAI real-time docs:
  https://www.assemblyai.com/docs/speech-to-text/streaming
"""

import os
import asyncio
import json
import time
import logging
import base64
import numpy as np
from faster_whisper import WhisperModel
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketState
from app.services.llm_processor import LLMProcessor
from app.risc_engine.database import _get_collection
from app.risc_engine.risk_engine import score_application, _audit_log
from app.services.face_verifier import FaceVerifier
import dotenv

# Load .env
dotenv.load_dotenv()

# Initialize Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Whisper model (load once)
logger.info("Loading Whisper model...")
try:
    whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    logger.info("Whisper model loaded successfully.")
except Exception as e:
    logger.error(f"Failed to load Whisper model: {e}")
    whisper_model = None

app = FastAPI()

# ── CORS ─────────────────────────────────────────────────────────────────────

allowed_origins = [
    o.strip()
    for o in os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/applications")
async def get_applications():
    """Fetch all stored loan applications for the employee dashboard."""
    coll = _get_collection()
    
    # Fallback to in-memory audit log if MongoDB is unavailable
    if coll is None:
        logger.info("MongoDB unavailable, serving %d records from in-memory audit log", len(_audit_log))
        return list(reversed(_audit_log))
    
    try:
        # Fetch applications, excluding internal _id, sorted by newest first
        cursor = coll.find({}, {"_id": 0}).sort("timestamp", -1)
        applications = list(cursor)
        
        # If DB is empty, maybe return in-memory as well?
        if not applications and _audit_log:
            return list(reversed(_audit_log))
            
        return applications
    except Exception as e:
        logger.error(f"Error fetching applications: {e}")
        return list(reversed(_audit_log))

# ── Config ────────────────────────────────────────────────────────────────────

_ASSEMBLYAI_RT_URL  = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"
# Alternative AAI URL if 404 persists: wss://api.assemblyai.com/v2/realtime?sample_rate=16000

_AGE_MISMATCH_TOLERANCE_YEARS = 10
_WINDOW_SECONDS               = 60
_MAX_CONN_PER_WINDOW          = 30     # Increased for development/strict mode
_LLM_DEBOUNCE_CHARS           = 2      # lower debounce for 1-word answers

_CONNECTION_WINDOW: dict[str, list[float]] = {}
_CONNECTION_LOCK = asyncio.Lock()


# ── Rate limiting ─────────────────────────────────────────────────────────────

async def enforce_connection_limit(client_key: str) -> bool:
    now = time.time()
    async with _CONNECTION_LOCK:
        history = _CONNECTION_WINDOW.setdefault(client_key, [])
        history[:] = [ts for ts in history if now - ts <= _WINDOW_SECONDS]
        if len(history) >= _MAX_CONN_PER_WINDOW:
            return False
        history.append(now)
        return True


# ── Default / merge applicant data ───────────────────────────────────────────

def get_default_applicant_data() -> dict:
    return {
        "interview_meta": {
            "full_name": "",
            "consent_video_recording": False,
            "consent_bureau_pull": False,
        },
        "customer_profile": {
            "age": 30,
            "employment_type": "salaried",
            "monthly_income": 50000.0,
            "employment_tenure_months": 24,
        },
        "loan_request": {
            "amount": 100000.0,
            "tenure_months": 36,
            "declared_emi_capacity": 5000.0,
        },
        "liabilities": {
            "existing_emis": 0.0,
            "credit_card_outstanding": 0.0,
        },
        "bureau": {
            "cibil_score": 750,
            "dpd_90_plus_count": 0,
            "enquiry_last_6_months": 1,
            "credit_utilization": 20.0,
            "has_npa": False,
            "has_settled_accounts": False,
            "credit_history_months": 36,
        },
        "verification": {"income_match_percent": 100.0, "age_mismatch_flag": False},
        "fraud_signals": {"geo_mismatch": False, "multiple_applications": False},
        "location_signals": {
            "ip_country": "IN",
            "ip_state": "Karnataka",
            "kyc_country": "IN",
            "kyc_state": "Karnataka",
            "vpn_or_proxy_detected": False,
        },
        "collateral": None,
    }


def merge_extracted_data(default_data: dict, extracted: dict) -> dict:
    meta = default_data["interview_meta"]
    prof = default_data["customer_profile"]
    loan = default_data["loan_request"]
    liab = default_data["liabilities"]
    frd  = default_data["fraud_signals"]
    bur  = default_data["bureau"]

    for key, target in [
        ("full_name",                 meta),
        ("consent_video_recording",   meta),
        ("consent_bureau_pull",       meta),
        ("age",                       prof),
        ("employment_type",           prof),
        ("monthly_income",            prof),
        ("employment_tenure_months",  prof),
        ("amount",                    loan),
        ("tenure_months",             loan),
        ("declared_emi_capacity",     loan),
        ("existing_emis",             liab),
        ("credit_card_outstanding",   liab),
        ("geo_mismatch",              frd),
        ("multiple_applications",     frd),
        ("cibil_score",               bur),
        ("credit_utilization",        bur),
        ("credit_history_months",     bur),
        ("dpd_90_plus_count",         bur),
    ]:
        if key in extracted:
            target[key] = extracted[key]

    return default_data


def sanitize_extracted_data(extracted) -> dict:
    if not isinstance(extracted, dict):
        return {}
    sanitized = {}
    numeric_fields = {
        "age": int, "employment_tenure_months": int, "tenure_months": int,
        "monthly_income": float, "amount": float, "declared_emi_capacity": float,
        "existing_emis": float, "credit_card_outstanding": float,
        "cibil_score": int, "credit_utilization": float, "credit_history_months": int,
        "dpd_90_plus_count": int,
    }
    bool_fields    = {"geo_mismatch", "multiple_applications", "answered_successfully",
                      "consent_video_recording", "consent_bureau_pull"}
    allowed_emp    = {"salaried", "self_employed", "business", "freelancer", "unemployed"}

    for key, caster in numeric_fields.items():
        if key in extracted and extracted[key] is not None:
            try:
                sanitized[key] = caster(extracted[key])
            except (TypeError, ValueError):
                pass
    for key in bool_fields:
        if isinstance(extracted.get(key), bool):
            sanitized[key] = extracted[key]
    if isinstance(extracted.get("full_name"), str) and extracted["full_name"].strip():
        sanitized["full_name"] = extracted["full_name"].strip()
    if extracted.get("employment_type") in allowed_emp:
        sanitized["employment_type"] = extracted["employment_type"]
    return sanitized


# ── Safe send ─────────────────────────────────────────────────────────────────

async def safe_send(ws: WebSocket, data: dict) -> bool:
    try:
        if ws.client_state == WebSocketState.CONNECTED:
            await ws.send_json(data)
            return True
    except Exception as exc:
        logger.warning("send failed type=%s err=%s", data.get("type"), exc)
    return False


# ── AssemblyAI real-time bridge ───────────────────────────────────────────────

async def whisper_realtime_bridge(
    client_ws: WebSocket,
    audio_queue: asyncio.Queue,
    transcript_queue: asyncio.Queue,
) -> None:
    """
    Local transcription bridge using faster-whisper.
    Processes raw PCM chunks from audio_queue.
    """
    if whisper_model is None:
        await safe_send(client_ws, {"type": "error", "message": "Whisper model not loaded."})
        return

    logger.info("Local Whisper transcription bridge started.")
    await safe_send(client_ws, {"type": "status", "message": "Local transcription active."})

    audio_buffer = np.array([], dtype=np.float32)
    chunk_count = 0
    
    try:
        while True:
            try:
                # Use a timeout to check for internal control signals
                chunk = await asyncio.wait_for(audio_queue.get(), timeout=0.1)
                if chunk is None:
                    break
                
                if isinstance(chunk, str) and chunk == "CLEAR_BUFFER":
                    logger.info("Whisper bridge: clearing audio buffer on request")
                    audio_buffer = np.array([], dtype=np.float32)
                    # Tell the frontend the buffer is reset
                    await safe_send(client_ws, {"type": "transcript_partial", "text": ""})
                    continue

                # Convert bytes (Int16) to float32 numpy array
                audio_chunk = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
                audio_buffer = np.append(audio_buffer, audio_chunk)
                chunk_count += 1
            except asyncio.TimeoutError:
                # No audio chunk, just continue the loop
                pass
            
            # Process every ~1 second (16000 samples) for better responsiveness with 1-word answers
            if len(audio_buffer) >= 16000:
                # Basic silence detection: skip if energy is very low
                # Increased threshold to 0.01 to filter out light air/background noise
                rms = np.sqrt(np.mean(audio_buffer**2))
                if rms < 0.015: # Significantly higher threshold for "clearly audible" speech
                    # If it's silent/noisy, we don't transcribe, but we might keep some of it
                    if len(audio_buffer) > 32000:
                        audio_buffer = audio_buffer[-8000:]
                    continue

                # Run transcription in a thread to not block the loop
                def transcribe():
                    # beam_size=1 is much faster for real-time
                    # condition_on_previous_text=False prevents hallucinations/repetition
                    # suppress_blank=True and higher no_speech_threshold help ignore noise
                    segments, info = whisper_model.transcribe(
                        audio_buffer, 
                        beam_size=1, 
                        language="en",
                        condition_on_previous_text=False,
                        initial_prompt="A short one-word answer for a loan interview.",
                        no_speech_threshold=0.6,  # Ignore if no speech confidence is high
                        log_prob_threshold=-1.0   # Require higher quality transcription
                    )
                    # Filter segments by confidence/no_speech_prob if possible
                    text_parts = []
                    for s in segments:
                        if s.no_speech_prob < 0.4: # Only keep segments likely to be speech
                            text_parts.append(s.text)
                    
                    text = "".join(text_parts).strip()
                    return text

                text = await asyncio.to_thread(transcribe)
                
                if text:
                    # Send partial/live transcript
                    await safe_send(client_ws, {"type": "transcript_partial", "text": text})
                    
                    # For 1-word answers, we want to treat even short segments as "final"
                    # so the LLM can start processing them.
                    if len(audio_buffer) >= 48000: # ~3 seconds
                        await transcript_queue.put(text)
                        await safe_send(client_ws, {"type": "transcript", "text": text})
                        # Keep very little context for 1-word answers
                        audio_buffer = audio_buffer[-4000:]
                
                # If buffer is too large, clear it
                if len(audio_buffer) > 96000: # 6 seconds
                    audio_buffer = audio_buffer[-8000:]

    except Exception as e:
        logger.error(f"Whisper bridge exception: {e}")
    finally:
        logger.info("Whisper bridge closed.")
        # Final attempt at transcription if buffer has data
        if len(audio_buffer) > 8000:
            try:
                def transcribe_final():
                    segments, _ = whisper_model.transcribe(audio_buffer, beam_size=5)
                    return "".join([s.text for s in segments]).strip()
                text = await asyncio.to_thread(transcribe_final)
                if text:
                    await transcript_queue.put(text)
                    await safe_send(client_ws, {"type": "transcript", "text": text})
            except: pass
        
        while not audio_queue.empty():
            try: audio_queue.get_nowait()
            except asyncio.QueueEmpty: break


# ── Main WebSocket endpoint ───────────────────────────────────────────────────

@app.websocket("/ws/audio")
async def audio_websocket(websocket: WebSocket):
    # Auth
    ws_auth_token = os.environ.get("WS_AUTH_TOKEN", "").strip()
    if ws_auth_token and websocket.query_params.get("token", "") != ws_auth_token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
        return

    # Rate limit
    client_host = websocket.client.host if websocket.client else "unknown"
    if not await enforce_connection_limit(client_host):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Rate limit exceeded")
        return

    # Note: ASSEMBLY_API_KEY is no longer required as we use local Whisper
    await websocket.accept()
    logger.info("Client connected: %s", client_host)

    # Session state
    llm_processor    = LLMProcessor(api_key=os.environ.get("GEMINI_API_KEY", ""))
    face_verifier    = FaceVerifier()
    applicant_data   = get_default_applicant_data()
    current_question = "Unknown Question"
    face_age         = -1
    face_task: asyncio.Task | None = None

    # Transcript accumulation
    confirmed_transcript = ""      # full session transcript (final segments only)
    last_llm_input       = ""      # last string we sent to LLM — debounce

    # Queues connecting this handler ↔ AssemblyAI bridge
    audio_queue      = asyncio.Queue(maxsize=500)
    transcript_queue = asyncio.Queue()

    # Start the local Whisper bridge as a background task
    bridge_task = asyncio.create_task(
        whisper_realtime_bridge(websocket, audio_queue, transcript_queue)
    )

    await safe_send(websocket, {"type": "status", "message": "Initialising local transcription..."})

    try:
        while True:
            # ── Handle newly arrived final transcripts (non-blocking) ──────
            while not transcript_queue.empty():
                new_text = transcript_queue.get_nowait()
                confirmed_transcript = (confirmed_transcript + " " + new_text).strip()

                # LLM extraction: debounce by requiring minimum new content
                new_chars = len(confirmed_transcript) - len(last_llm_input)
                if new_chars >= _LLM_DEBOUNCE_CHARS:
                    last_llm_input = confirmed_transcript
                    llm_query = (
                        f"Context Question: {current_question} | "
                        f"Applicant Answer Delta: {new_text}"
                    )
                    try:
                        extracted = sanitize_extracted_data(
                            await llm_processor.extract_structured_data(llm_query)
                        )
                    except Exception as e:
                        logger.warning("LLM extraction error: %s", e)
                        extracted = {}

                    if extracted:
                        applicant_data = merge_extracted_data(applicant_data, extracted)

                        # Age mismatch check
                        if "age" in extracted and face_age > 0:
                            mismatch = abs(extracted["age"] - face_age) > _AGE_MISMATCH_TOLERANCE_YEARS
                            applicant_data["verification"]["age_mismatch_flag"] = mismatch

                        # Advance question if answer accepted
                        if extracted.get("answered_successfully") is True:
                            await safe_send(websocket, {"type": "advance_question"})

                        # Risk score (non-blocking)
                        try:
                            risk_result = await asyncio.to_thread(
                                score_application, applicant_data
                            )
                            await safe_send(websocket, {
                                "type": "risk_result",
                                "data": risk_result,
                                "extracted_fields": extracted,
                                "summary": {
                                    "full_name":               applicant_data["interview_meta"]["full_name"],
                                    "consent_video_recording": applicant_data["interview_meta"]["consent_video_recording"],
                                    "consent_bureau_pull":     applicant_data["interview_meta"]["consent_bureau_pull"],
                                    "age":                     applicant_data["customer_profile"]["age"],
                                    "employment_type":         applicant_data["customer_profile"]["employment_type"],
                                    "monthly_income":          applicant_data["customer_profile"]["monthly_income"],
                                    "employment_tenure_months":applicant_data["customer_profile"]["employment_tenure_months"],
                                    "loan_amount":             applicant_data["loan_request"]["amount"],
                                    "loan_tenure_months":      applicant_data["loan_request"]["tenure_months"],
                                    "declared_emi_capacity":   applicant_data["loan_request"]["declared_emi_capacity"],
                                    "existing_emis":           applicant_data["liabilities"]["existing_emis"],
                                    "credit_card_outstanding": applicant_data["liabilities"]["credit_card_outstanding"],
                                },
                            })
                        except Exception as e:
                            logger.exception("Risk engine failed: %s", e)
                            await safe_send(websocket, {"type": "error", "message": "Risk scoring failed."})

            # ── Receive next client message ───────────────────────────────
            if bridge_task.done() and not bridge_task.cancelled():
                try:
                    # Check if bridge task raised an exception
                    exc = bridge_task.exception()
                    if exc:
                        logger.error(f"AAI Bridge task failed with exception: {exc}")
                        await safe_send(websocket, {"type": "error", "message": f"Transcription bridge failed: {exc}"})
                except (asyncio.CancelledError, asyncio.InvalidStateError):
                    pass
                # If bridge is dead, we might want to break or try to restart.
                # For now, let's just log and continue, but we won't be able to transcribe.

            try:
                message = await websocket.receive()
            except RuntimeError as re:
                # Catch "Cannot call receive once a disconnect message has been received"
                logger.info("WebSocket loop: receive failed (already disconnected)")
                break

            if message["type"] == "websocket.disconnect":
                logger.info("WebSocket loop: received disconnect signal")
                break

            if "text" in message:
                try:
                    payload = json.loads(message["text"])
                    msg_type = payload.get("type")

                    if msg_type == "set_question":
                        current_question = payload.get("question", "")

                    elif msg_type == "clear_buffer":
                        # Drain the queue to discard old audio chunks immediately
                        while not audio_queue.empty():
                            try:
                                audio_queue.get_nowait()
                            except asyncio.QueueEmpty:
                                break
                        
                        try:
                            audio_queue.put_nowait("CLEAR_BUFFER")
                        except asyncio.QueueFull:
                            pass

                    elif msg_type == "face_image":
                        async def run_face_verify(img=payload.get("image")):
                            nonlocal face_age
                            # Retry face verification up to 3 times if no faces found
                            for attempt in range(3):
                                age = await asyncio.to_thread(face_verifier.verify_age, img)
                                if age > 0:
                                    face_age = age
                                    declared = applicant_data["customer_profile"]["age"]
                                    if declared and abs(declared - face_age) > _AGE_MISMATCH_TOLERANCE_YEARS:
                                        applicant_data["verification"]["age_mismatch_flag"] = True
                                    break
                                elif attempt < 2:
                                    logger.info(f"Face verification attempt {attempt+1} failed, retrying...")
                                    await asyncio.sleep(1) # Wait a bit before retry

                        if face_task and not face_task.done():
                            face_task.cancel()
                        face_task = asyncio.create_task(run_face_verify())

                except json.JSONDecodeError:
                    logger.warning("Invalid text payload dropped.")

            elif "bytes" in message:
                if bridge_task.done():
                    # If bridge is dead, don't bother pushing audio.
                    # Instead, we might want to alert the user.
                    continue

                chunk = message["bytes"]
                if len(chunk) > 512 * 1024:
                    logger.warning("Oversized audio chunk dropped (%d bytes)", len(chunk))
                    continue
                try:
                    audio_queue.put_nowait(chunk)
                except asyncio.QueueFull:
                    # Bridge is slow or stuck — drain the oldest chunk and put newest.
                    try:
                        audio_queue.get_nowait()
                        audio_queue.put_nowait(chunk)
                    except asyncio.QueueEmpty:
                        audio_queue.put_nowait(chunk)
                    logger.warning("Audio queue full — dropped oldest chunk.")

    except WebSocketDisconnect:
        logger.info("Client disconnected: %s", client_host)
    except Exception as e:
        logger.exception("WebSocket error: %s", e)
    finally:
        # Shut down the bridge cleanly
        try:
            # Use put_nowait or a timeout to avoid hanging if bridge failed
            audio_queue.put_nowait(None)
        except asyncio.QueueFull:
            # Drain one then put None if full, or just ignore since we're cancelling anyway
            try:
                audio_queue.get_nowait()
                audio_queue.put_nowait(None)
            except:
                pass

        bridge_task.cancel()
        if face_task and not face_task.done():
            face_task.cancel()

        # Wait for bridge task to actually cancel to avoid lingering
        try:
            await bridge_task
        except asyncio.CancelledError:
            pass