import requests
import time
import os
from dotenv import load_dotenv

# 🔹 Load .env
load_dotenv(dotenv_path=".env")

API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

if not API_KEY:
    print("❌ API key not found in .env")
    exit()
else:
    print("✅ API key loaded")


# 🔹 Step 1: Upload audio
def upload_file(filename):
    upload_url = "https://api.assemblyai.com/v2/upload"

    headers = {
        "authorization": API_KEY
    }

    def read_file():
        with open(filename, "rb") as f:
            while chunk := f.read(5 * 1024 * 1024):
                yield chunk

    response = requests.post(upload_url, headers=headers, data=read_file())

    print("📡 Upload status:", response.status_code)
    print("📡 Upload response:", response.text)

    if response.status_code != 200:
        raise Exception("❌ Upload failed")

    return response.json()["upload_url"]


# 🔹 Step 2: Request transcription
def transcribe(audio_url):
    transcript_url = "https://api.assemblyai.com/v2/transcript"

    headers = {
        "authorization": API_KEY,
        "content-type": "application/json"
    }

    data = {
        "audio_url": audio_url,
        "speech_models": ["universal"]
    }

    response = requests.post(transcript_url, json=data, headers=headers)

    print("📡 Transcribe status:", response.status_code)
    print("📡 Transcribe response:", response.text)

    if response.status_code != 200:
        raise Exception("❌ Transcription request failed")

    return response.json()["id"]


# 🔹 Step 3: Poll result
def get_result(transcript_id):
    polling_url = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"

    headers = {
        "authorization": API_KEY
    }

    while True:
        response = requests.get(polling_url, headers=headers)
        data = response.json()

        status = data["status"]

        if status == "completed":
            return data["text"]

        elif status == "error":
            raise Exception(data["error"])

        print("⏳ Processing...")
        time.sleep(3)


# 🔥 MAIN
file_path = "audioo.mp3"

try:
    print("📤 Uploading...")
    audio_url = upload_file(file_path)

    print("🧠 Transcribing...")
    transcript_id = transcribe(audio_url)

    print("⌛ Waiting for result...")
    text = get_result(transcript_id)

    print("\n📝 Transcription:")
    print(text)

except FileNotFoundError:
    print("❌ audio.mp3 not found in folder")

except Exception as e:
    print("❌ ERROR:", e)