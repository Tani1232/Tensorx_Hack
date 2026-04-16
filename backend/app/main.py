import os
import tempfile
import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import whisper
from app.services.llm_processor import LLMProcessor
from app.risc_engine.risk_engine import score_application
from app.services.face_verifier import FaceVerifier
import dotenv

dotenv.load_dotenv()

app = FastAPI()

# Allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = None
is_loading = False

async def get_model():
    global model, is_loading
    if model is None:
        if is_loading:
            while model is None:
                await asyncio.sleep(0.5)
            return model
            
        is_loading = True
        print("\n--- Lazy Loading Whisper 'base' Model ---")
        model = await asyncio.to_thread(whisper.load_model, "base")
        print("--- Whisper Model Loaded Successfully ---\n")
        is_loading = False
    return model

# Prepare default applicant data
def get_default_applicant_data():
    return {
        "customer_profile": {
            "age": 30,
            "employment_type": "salaried",
            "monthly_income": 50000.0,
            "employment_tenure_months": 24
        },
        "loan_request": {
            "amount": 100000.0,
            "tenure_months": 36,
            "declared_emi_capacity": 5000.0
        },
        "liabilities": {
            "existing_emis": 0.0,
            "credit_card_outstanding": 0.0
        },
        "bureau": {
            "cibil_score": 750,
            "dpd_90_plus_count": 0,
            "enquiry_last_6_months": 1,
            "credit_utilization": 20.0,
            "has_npa": False,
            "has_settled_accounts": False,
            "credit_history_months": 36
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
        "collateral": None
    }

def merge_extracted_data(default_data: dict, extracted: dict) -> dict:
    if "age" in extracted:
        default_data["customer_profile"]["age"] = extracted["age"]
    if "employment_type" in extracted:
        default_data["customer_profile"]["employment_type"] = extracted["employment_type"]
    if "monthly_income" in extracted:
        default_data["customer_profile"]["monthly_income"] = extracted["monthly_income"]
    if "employment_tenure_months" in extracted:
        default_data["customer_profile"]["employment_tenure_months"] = extracted["employment_tenure_months"]
    
    if "amount" in extracted:
        default_data["loan_request"]["amount"] = extracted["amount"]
    if "tenure_months" in extracted:
        default_data["loan_request"]["tenure_months"] = extracted["tenure_months"]
    if "declared_emi_capacity" in extracted:
        default_data["loan_request"]["declared_emi_capacity"] = extracted["declared_emi_capacity"]
        
    if "existing_emis" in extracted:
        default_data["liabilities"]["existing_emis"] = extracted["existing_emis"]
    if "credit_card_outstanding" in extracted:
        default_data["liabilities"]["credit_card_outstanding"] = extracted["credit_card_outstanding"]
        
    if "geo_mismatch" in extracted:
        default_data["fraud_signals"]["geo_mismatch"] = extracted["geo_mismatch"]
    if "multiple_applications" in extracted:
        default_data["fraud_signals"]["multiple_applications"] = extracted["multiple_applications"]
        
    return default_data


@app.websocket("/ws/audio")
async def audio_websocket(websocket: WebSocket):
    await websocket.accept()
    print("New WebSocket connection established.")
    
    api_key = os.environ.get("GEMINI_API_KEY", "AIzaSyBQrF61wV32rpPsGOMyXYGARnvxDNKIcbA")
    llm_processor = LLMProcessor(api_key=api_key)
    face_verifier = FaceVerifier()
    
    await websocket.send_json({"type": "status", "message": "Initializing AI Model... Give it a moment."})
    local_model = await get_model()
    await websocket.send_json({"type": "status", "message": "Model Active! Listening to your audio..."})
    
    audio_buffer = bytearray()
    last_llm_prompt = ""
    last_processed_idx = 0
    applicant_data = get_default_applicant_data()
    current_question = "Unknown Question"
    face_age = -1
    
    try:
        while True:
            message = await websocket.receive()
            
            if "text" in message:
                try:
                    payload = json.loads(message["text"])
                    if payload.get("type") == "set_question":
                        current_question = payload.get("question", "")
                    elif payload.get("type") == "face_image":
                        # Verify age asynchronously off the main event loop
                        async def run_face_verify():
                            nonlocal face_age, applicant_data
                            age = await asyncio.to_thread(face_verifier.verify_age, payload.get("image"))
                            if age > 0:
                                face_age = age
                                if applicant_data["customer_profile"]["age"] and abs(applicant_data["customer_profile"]["age"] - face_age) > 5:
                                    applicant_data["verification"]["age_mismatch_flag"] = True
                        asyncio.create_task(run_face_verify())
                except json.JSONDecodeError:
                    pass
            elif "bytes" in message:
                data = message["bytes"]
                audio_buffer.extend(data)
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
                    tmp.write(audio_buffer)
                    tmp_path = tmp.name
                    
                try:
                    result = await asyncio.to_thread(local_model.transcribe, tmp_path, fp16=False)
                    transcript_text = result.get("text", "").strip()
                    
                    if transcript_text:
                        delta_text = transcript_text[last_processed_idx:].strip()
                        if delta_text:
                            print(f"\n[USER] (answering Q: '{current_question[:30]}...'): {delta_text}")
                            await websocket.send_json({"type": "transcript", "text": transcript_text})
                            
                            if transcript_text != last_llm_prompt and len(delta_text) > 20 and delta_text[-1] in ".?!":
                                # Process LLM structure with just the delta and current question
                                llm_query = f"Context Question: {current_question} | Applicant Answer Delta: {delta_text}"
                                print(f"\n[SENDING TO LLM]: {llm_query}")
                                
                                extracted = await llm_processor.extract_structured_data(llm_query)
                                
                                if extracted:
                                    print(f"\n[EXTRACTED FROM LLM]: {json.dumps(extracted, indent=2)}")
                                    applicant_data = merge_extracted_data(applicant_data, extracted)
                                    
                                    # Trigger re-eval of face age mismatch if LLM just extracted age
                                    if "age" in extracted and face_age > 0:
                                        if abs(extracted["age"] - face_age) > 5:
                                            applicant_data["verification"]["age_mismatch_flag"] = True
                                        else:
                                            applicant_data["verification"]["age_mismatch_flag"] = False

                                    # Check auto-advance signal
                                    if extracted.get("answered_successfully") is True:
                                        print("\n[AI DECISION]: Question Answered Successfully. Advancing...")
                                        await websocket.send_json({"type": "advance_question"})

                                    try:
                                        # Trigger scoring logic
                                        risk_result = score_application(applicant_data)
                                        await websocket.send_json({
                                            "type": "risk_result",
                                            "data": risk_result,
                                            "extracted_fields": extracted
                                        })
                                    except Exception as e:
                                        pass
                                        
                                last_llm_prompt = transcript_text
                                last_processed_idx = len(transcript_text)
                except Exception as e:
                    print(f"Transcription Execution Error: {e}")
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                        
    except WebSocketDisconnect:
        print("WebSocket client disconnected.")
    except Exception as e:
        print(f"WebSocket Error: {e}")
