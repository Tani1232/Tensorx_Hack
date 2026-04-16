# AI Loan Officer Onboarding Engine

A fully autonomous, full-stack video and audio AI interviewer system capable of handling end-to-end loan onboarding. It conducts a guided KYC conversation, processes real-time audio transcripts via Whisper and Gemini, flags fraudulent behavior visually, and outputs automated underwriting decisions using a custom weighted scoring engine and eligibility computation.

## Key Features

- **Autonomous Interview Interface**: Built with Next.js, Framer Motion, and Tailwind CSS. The interface manages the applicant pacing asynchronously. It streams audio bi-directionally, captures visual verification frames, and auto-advances the interview flow using backend AI heuristics without requiring manual intervention.
- **Real-Time Streaming**: Implements WebSocket (`/ws/audio`) architecture in a FastAPI backend to ingest live WebM Opus chunks directly parsed from browser MediaRecorder tracks.
- **Dynamic Speech-to-Text**: Employs OpenAI's Whisper model (lazy-loaded natively) to incrementally transcribe applicant speech without imposing latency constraints.
- **Context-Aware Semantic Extraction**: Submits transcript Deltas mapped exclusively to the Active Interview Question into Google's `gemini-2.5-flash` model. Gemini runs a strict pass/fail heuristic to dictate progression metrics whilst extracting structured data elements (Income, Age, Existent EMI).
- **Risk & Fraud Underwriting**: Extracted data is instantly funneled into a strictly-typed Pydantic validation system. The risk engine computes weighted limits evaluating FOIR (Fixed Obligations to Income Ratio), credit score thresholds, location signals, collateral buffers, and applies deterministic hard-declines for strict fraud flags.
- **Eligibility Engine**: Synchronized algorithms compute the maximum potential loan amount relative to verifiable income and declared collateral, automatically scaling or determining counter-offer adjustments dynamically.
- **Automated Verification**: Asynchronously intercepts camera frames (Canvas -> Data URI) and relays them against the Face++ verification API, detecting visual demographic disparities and enforcing an override threshold on the live dashboard.

## Technology Stack

- **Frontend**: Next.js 16 (App Router), React 19, Tailwind CSS v4, shadcn/ui
- **Backend**: FastAPI, Python 3.14, Uvicorn, WebSockets
- **AI/ML Layer**: openai-whisper (STT), gemini-2.5-flash (NLP), Face++ (Visual Verification)

---

## Deployment Instructions

### 1. Environment Configuration

Before running the system natively, establish the necessary environment variables across your workspaces. 

Create a `.env` file inside the `backend/` directory:

```env
GEMINI_API_KEY=your_gemini_api_key_here
FACE_API_KEY=your_face_plus_plus_api_key
FACE_API_SECRET=your_face_plus_plus_api_secret
```

### 2. Initializing the Backend (FastAPI / Machine Learning Core)

Open a terminal session and isolate your Python scope to load the ML dependencies natively.

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app
```

Note: Depending on the hardware capabilities of the execution runtime, assigning the local Whisper AI weights into memory may require 5-15 seconds asynchronously upon the first web socket invocation.

### 3. Initializing the Frontend (Next.js Application)

Open a new, separate terminal tab to build and run the client-side workspace.

```bash
cd frontend
npm install
npm run dev
```

### 4. Running an Interview Session

1. Navigate to `http://localhost:3000` via a supported web browser (e.g., Google Chrome).
2. Ensure you grant the browser permission parameters to access both your Camera and Microphone.
3. Click on the central "Click to Start Session" button to open the secure websocket transmission node and dispatch the visual verification frame.
4. Begin articulating answers to the contextual prompts displayed actively on the UI layer. The system will autonomously transcribe speech, compute variables on the analytical console, and push application states until a definitive risk vector is calculated.
