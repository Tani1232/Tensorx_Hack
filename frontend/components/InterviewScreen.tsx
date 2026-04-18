'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ShieldCheck,
  Video,
  Mic,
  MicOff,
  VideoOff,
  PhoneOff,
  Activity,
  CheckCircle2,
  Circle,
  AlertCircle,
  ChevronRight,
  TrendingUp,
  Banknote,
  Briefcase,
  Clock,
  CreditCard,
  User,
  BarChart2,
  X,
  Menu,
} from 'lucide-react';
import { INTERVIEW_QUESTIONS, type Question } from '../lib/questions';
import { ScoreRing } from './ui/score-ring';

// ─── Types ────────────────────────────────────────────────────────────────────
type RiskResult = {
  decision: 'APPROVE' | 'DECLINE' | 'REVIEW' | 'REDUCE';
  risk_score: number;
  risk_band: string;
  top_factors: string[];
  flags: string[];
  llm_explanation: string;
};

type ExtractedData = {
  full_name?: string;
  consent_video_recording?: boolean;
  consent_bureau_pull?: boolean;
  monthly_income?: number;
  employment_tenure_months?: number;
  employment_type?: string;
  amount?: number;
  tenure_months?: number;
  declared_emi_capacity?: number;
  existing_emis?: number;
  credit_card_outstanding?: number;
  age?: number;
  cibil_score?: number;
  credit_utilization?: number;
  credit_history_months?: number;
  dpd_90_plus_count?: number;
};

type SessionSummary = {
  full_name: string;
  consent_video_recording: boolean;
  consent_bureau_pull: boolean;
  age: number;
  employment_type: string;
  monthly_income: number;
  employment_tenure_months: number;
  loan_amount: number;
  loan_tenure_months: number;
  declared_emi_capacity: number;
  existing_emis: number;
  credit_card_outstanding: number;
  cibil_score?: number;
  credit_utilization?: number;
  credit_history_months?: number;
  dpd_90_plus_count?: number;
};

// ─── Constants ────────────────────────────────────────────────────────────────
const SECTIONS = Array.from(new Set(INTERVIEW_QUESTIONS.map(q => q.section)));

const DECISION_CONFIG = {
  APPROVE: { label: 'Approved',     color: '#10B981', bg: 'rgba(16,185,129,0.08)',  border: 'rgba(16,185,129,0.20)' },
  DECLINE: { label: 'Declined',     color: '#EF4444', bg: 'rgba(239,68,68,0.08)',   border: 'rgba(239,68,68,0.20)'  },
  REVIEW:  { label: 'Under Review', color: '#F59E0B', bg: 'rgba(245,158,11,0.08)',  border: 'rgba(245,158,11,0.20)' },
  REDUCE:  { label: 'Reduced Offer', color: '#3B82F6', bg: 'rgba(59,130,246,0.08)', border: 'rgba(59,130,246,0.20)' },
};

function formatCurrency(v: number) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency', currency: 'INR', maximumFractionDigits: 0,
  }).format(v);
}

function boolText(value?: boolean) {
  if (value === true) return 'Yes';
  if (value === false) return 'No';
  return '—';
}

// ─── SectionNav (left sidebar, desktop only) ──────────────────────────────────
function SectionNav({
  sections, currentSection, activeQIndex, totalQ,
}: {
  sections: string[]; currentSection: string; activeQIndex: number; totalQ: number;
}) {
  const currentSectionIdx = sections.indexOf(currentSection);
  const pct = Math.round(((activeQIndex + 1) / totalQ) * 100);

  return (
    <aside
      className="hidden lg:flex flex-col border-r"
      style={{
        width: 264, minWidth: 264, background: '#0A0D12',
        borderColor: 'rgba(255,255,255,0.06)', padding: '24px 0',
      }}
    >
      {/* Brand */}
      <div className="flex items-center gap-2.5 px-6 mb-8">
        <div className="flex items-center justify-center rounded-lg" style={{ width: 32, height: 32, background: 'rgba(59,111,212,0.15)', border: '1px solid rgba(59,111,212,0.25)' }}>
          <ShieldCheck size={16} color="#3B6FD4" strokeWidth={2} />
        </div>
        <div>
          <p className="text-sm font-semibold" style={{ color: '#F1F5F9', lineHeight: 1.2 }}>LoanAI</p>
          <p className="text-xs" style={{ color: '#64748B' }}>Secure Assessment</p>
        </div>
      </div>

      {/* Progress */}
      <div className="px-6 mb-6">
        <div className="flex justify-between items-center mb-2">
          <span className="text-xs font-medium" style={{ color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Progress</span>
          <span className="text-xs font-mono font-semibold" style={{ color: '#3B6FD4' }}>{pct}%</span>
        </div>
        <div style={{ height: 2, background: 'rgba(255,255,255,0.06)', borderRadius: 999, overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${pct}%`, background: '#3B6FD4', borderRadius: 999, transition: 'width 0.6s cubic-bezier(0.16,1,0.3,1)', boxShadow: '0 0 8px rgba(59,111,212,0.5)' }} />
        </div>
      </div>

      {/* Steps */}
      <nav className="flex-1 px-4 space-y-1 overflow-y-auto">
        {sections.map((sec, idx) => {
          const isPast   = idx < currentSectionIdx;
          const isActive = idx === currentSectionIdx;
          return (
            <div key={sec} className="flex items-start gap-3 rounded-lg px-3 py-2.5 transition-all duration-300"
              style={{ background: isActive ? 'rgba(59,111,212,0.10)' : 'transparent', opacity: isPast || isActive ? 1 : 0.35 }}>
              <div className="mt-0.5 flex-shrink-0">
                {isPast  ? <CheckCircle2 size={16} color="#10B981" strokeWidth={2} /> :
                 isActive ? <div className="animate-pulse-dot" style={{ width: 16, height: 16, borderRadius: '50%', border: '2px solid #3B6FD4', background: 'rgba(59,111,212,0.20)' }} /> :
                            <Circle size={16} color="#374151" strokeWidth={1.5} />}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium leading-snug truncate"
                  style={{ color: isActive ? '#F1F5F9' : isPast ? '#94A3B8' : '#374151' }}>{sec}</p>
                {isActive && <p className="text-xs mt-0.5" style={{ color: '#3B6FD4' }}>In progress</p>}
                {isPast  && <p className="text-xs mt-0.5" style={{ color: '#10B981' }}>Complete</p>}
              </div>
            </div>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-6 pt-4 mt-2" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        <p className="text-xs" style={{ color: '#374151' }}>End-to-end encrypted</p>
        <p className="text-xs mt-0.5" style={{ color: '#374151' }}>RBI compliant · KYC verified</p>
      </div>
    </aside>
  );
}

// ─── Mobile section nav sheet ─────────────────────────────────────────────────
function MobileSectionSheet({
  open, onClose, sections, currentSection, activeQIndex, totalQ,
}: {
  open: boolean; onClose: () => void;
  sections: string[]; currentSection: string; activeQIndex: number; totalQ: number;
}) {
  const currentSectionIdx = sections.indexOf(currentSection);
  const pct = Math.round(((activeQIndex + 1) / totalQ) * 100);

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div key="backdrop" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)', zIndex: 40 }} />
          <motion.div key="sheet" initial={{ x: '-100%' }} animate={{ x: 0 }} exit={{ x: '-100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 320, mass: 0.9 }}
            style={{
              position: 'fixed', top: 0, left: 0, bottom: 0, zIndex: 50, width: 280,
              background: '#0A0D12', borderRight: '1px solid rgba(255,255,255,0.08)',
              display: 'flex', flexDirection: 'column', padding: '24px 0',
            }}
          >
            <div className="flex items-center justify-between px-5 mb-6">
              <div className="flex items-center gap-2">
                <ShieldCheck size={16} color="#3B6FD4" />
                <span className="text-sm font-semibold" style={{ color: '#F1F5F9' }}>LoanAI</span>
              </div>
              <button aria-label="Close section navigation" onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4 }}>
                <X size={18} color="#64748B" />
              </button>
            </div>

            {/* Progress */}
            <div className="px-5 mb-5">
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs font-medium" style={{ color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Progress</span>
                <span className="text-xs font-mono font-semibold" style={{ color: '#3B6FD4' }}>{pct}%</span>
              </div>
              <div style={{ height: 2, background: 'rgba(255,255,255,0.06)', borderRadius: 999, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${pct}%`, background: '#3B6FD4', borderRadius: 999, transition: 'width 0.6s cubic-bezier(0.16,1,0.3,1)' }} />
              </div>
            </div>

            {/* Steps */}
            <nav className="flex-1 px-4 space-y-1 overflow-y-auto">
              {sections.map((sec, idx) => {
                const isPast = idx < currentSectionIdx;
                const isActive = idx === currentSectionIdx;
                return (
                  <button type="button" aria-label={`Section ${sec}`} key={sec} onClick={onClose} className="flex w-full text-left items-start gap-3 rounded-lg px-3 py-2.5"
                    style={{ background: isActive ? 'rgba(59,111,212,0.10)' : 'transparent', opacity: isPast || isActive ? 1 : 0.35 }}>
                    <div className="mt-0.5 flex-shrink-0">
                      {isPast  ? <CheckCircle2 size={16} color="#10B981" strokeWidth={2} /> :
                       isActive ? <div className="animate-pulse-dot" style={{ width: 16, height: 16, borderRadius: '50%', border: '2px solid #3B6FD4', background: 'rgba(59,111,212,0.20)' }} /> :
                                  <Circle size={16} color="#374151" strokeWidth={1.5} />}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium leading-snug truncate"
                        style={{ color: isActive ? '#F1F5F9' : isPast ? '#94A3B8' : '#374151' }}>{sec}</p>
                      {isActive && <p className="text-xs mt-0.5" style={{ color: '#3B6FD4' }}>In progress</p>}
                      {isPast  && <p className="text-xs mt-0.5" style={{ color: '#10B981' }}>Complete</p>}
                    </div>
                  </button>
                );
              })}
            </nav>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

// ─── InterviewResults (displayed after completion) ──────────────────────────
function InterviewResults({
   questions,
   answers,
   riskResult,
   sessionSummary,
   onReset,
 }: {
   questions: Question[];
   answers: string[];
   riskResult: RiskResult | null;
   sessionSummary: SessionSummary | null;
   onReset: () => void;
 }) {
  const decisionCfg = riskResult ? (DECISION_CONFIG[riskResult.decision] ?? DECISION_CONFIG.REVIEW) : null;

  if (!riskResult || !decisionCfg) {
    return (
      <div style={{
        minHeight: '100dvh',
        background: '#080A0E',
        color: '#F1F5F9',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 24,
        padding: 40
      }}>
        <div className="animate-pulse" style={{ width: 80, height: 80, borderRadius: 20, background: 'rgba(59,111,212,0.1)', border: '1px solid rgba(59,111,212,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Activity size={40} color="#3B6FD4" />
        </div>
        <div style={{ textAlign: 'center' }}>
          <h2 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>Analyzing Results...</h2>
          <p style={{ color: '#64748B' }}>Our AI is calculating your risk profile and generating the final assessment.</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{
      minHeight: '100dvh',
      background: '#080A0E',
      color: '#F1F5F9',
      padding: '40px 24px',
      overflowY: 'auto',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center'
    }}>
      <div style={{ maxWidth: 800, width: '100%' }}>
        <header style={{ marginBottom: 40, textAlign: 'center' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: 'rgba(59,111,212,0.15)', border: '1px solid rgba(59,111,212,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <ShieldCheck size={20} color="#3B6FD4" />
            </div>
            <h1 style={{ fontSize: 24, fontWeight: 700, letterSpacing: '-0.02em' }}>Assessment Summary</h1>
          </div>
          <p style={{ color: '#64748B', fontSize: 16 }}>Your interview has been completed and analyzed by our AI system.</p>
        </header>

        <section style={{ marginBottom: 40 }}>
          <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 20, display: 'flex', alignItems: 'center', gap: 10 }}>
            <Activity size={18} color="#3B6FD4" />
            Interview Transcripts
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {questions.map((q, idx) => (
              <div key={q.id} style={{
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: 16,
                padding: 20,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                  <span style={{ fontSize: 11, fontWeight: 700, color: '#3B6FD4', background: 'rgba(59,111,212,0.1)', padding: '2px 8px', borderRadius: 99 }}>Q{idx + 1}</span>
                  <span style={{ fontSize: 12, fontWeight: 500, color: '#64748B' }}>{q.section}</span>
                </div>
                <p style={{ fontSize: 15, fontWeight: 500, color: '#F1F5F9', marginBottom: 12, lineHeight: 1.5 }}>{q.text}</p>
                <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: 12, padding: 16, border: '1px solid rgba(255,255,255,0.04)' }}>
                  <p style={{ fontSize: 14, color: '#94A3B8', fontStyle: 'italic', margin: 0, lineHeight: 1.6 }}>
                    {answers[idx] || 'No response captured.'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>

        <div style={{
          background: 'rgba(59,111,212,0.05)',
          border: '1px solid rgba(59,111,212,0.1)',
          borderRadius: 16,
          padding: 20,
          textAlign: 'center',
          marginBottom: 40
        }}>
          <p style={{ fontSize: 14, color: '#94A3B8' }}>
            Your interview data has been securely submitted for review. 
            A bank representative will contact you shortly regarding your application status.
          </p>
        </div>

        <div style={{ display: 'flex', justifyContent: 'center', marginTop: 0 }}>
          <button
            onClick={onReset}
            style={{
              padding: '12px 32px',
              borderRadius: 999,
              background: '#3B6FD4',
              color: 'white',
              fontSize: 16,
              fontWeight: 600,
              border: 'none',
              cursor: 'pointer',
              boxShadow: '0 10px 20px rgba(59,111,212,0.2)',
              transition: 'all 0.2s ease'
            }}
            onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-2px)'}
            onMouseLeave={e => e.currentTarget.style.transform = 'translateY(0)'}
          >
            Start New Session
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main Component ────────────────────────────────────────────────────────────
export default function InterviewScreen() {
  const videoRef         = useRef<HTMLVideoElement>(null);
  const wsRef            = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const faceCaptureTimeoutRef = useRef<number | null>(null);

  const audioContextRef   = useRef<AudioContext | null>(null);
  const processorRef      = useRef<ScriptProcessorNode | null>(null);
  const streamRef         = useRef<MediaStream | null>(null);

  const [isConnected, setIsConnected]         = useState(false);
  const [isStarting, setIsStarting]           = useState(false);
  const [isMicOn, setIsMicOn]                 = useState(true);
  const [isVideoOn, setIsVideoOn]             = useState(true);
  const [transcript, setTranscript]           = useState('');
  const [activeQIndex, setActiveQIndex]       = useState(0);
  const activeQIndexRef                       = useRef(0);
  const [answers, setAnswers]                 = useState<string[]>(new Array(INTERVIEW_QUESTIONS.length).fill(''));
  const [isFinished, setIsFinished]           = useState(false);

  // Update ref whenever state changes
  useEffect(() => {
    activeQIndexRef.current = activeQIndex;
  }, [activeQIndex]);
  const [extractedData, setExtractedData]     = useState<ExtractedData>({});
  const [riskResult, setRiskResult]           = useState<RiskResult | null>(null);
  const [systemStatus, setSystemStatus]       = useState('Ready to begin');
  const [sessionId, setSessionId]             = useState('');
  const [showSectionNav, setShowSectionNav]   = useState(false);
  const [sessionSummary, setSessionSummary]   = useState<SessionSummary | null>(null);

  useEffect(() => {
    const d = new Date();
    const pad = (n: number) => String(n).padStart(2, '0');
    setSessionId(`${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} · ${String(Math.floor(Math.random()*90000+10000))}`);
  }, []);

  const hasQuestions = INTERVIEW_QUESTIONS.length > 0;
  const currentQ = hasQuestions ? INTERVIEW_QUESTIONS[Math.min(activeQIndex, INTERVIEW_QUESTIONS.length - 1)] : null;
  const progressPct = hasQuestions ? ((activeQIndex + 1) / INTERVIEW_QUESTIONS.length) * 100 : 0;

  useEffect(() => {
    if (!currentQ) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify({ type: 'set_question', question: currentQ.text }));
      } catch {
        setSystemStatus('Connection interrupted');
      }
    }
  }, [activeQIndex, currentQ]);

  const startSession = useCallback(async () => {
    if (isStarting || isConnected || !currentQ) return;
    setIsStarting(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;

      setSystemStatus('Connecting...');
      const wsBase = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000/ws/audio';
      const token = process.env.NEXT_PUBLIC_WS_AUTH_TOKEN;
      const wsUrl = token ? `${wsBase}${wsBase.includes('?') ? '&' : '?'}token=${encodeURIComponent(token)}` : wsBase;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setIsStarting(false);
        setSystemStatus('AI Model loading...');
        setSessionSummary(null);

        // PCM Audio Capture (16kHz S16LE)
        const audioContext = new AudioContext({ sampleRate: 16000 });
        audioContextRef.current = audioContext;
        const source = audioContext.createMediaStreamSource(stream);
        const processor = audioContext.createScriptProcessor(4096, 1, 1);
        processorRef.current = processor;

        processor.onaudioprocess = (e) => {
          if (ws.readyState === WebSocket.OPEN) {
            const inputData = e.inputBuffer.getChannelData(0);
            // Convert Float32 to Int16 PCM
            const pcmData = new Int16Array(inputData.length);
            for (let i = 0; i < inputData.length; i++) {
              pcmData[i] = Math.max(-1, Math.min(1, inputData[i])) * 0x7FFF;
            }
            ws.send(pcmData.buffer);
          }
        };

        source.connect(processor);
        processor.connect(audioContext.destination);

        ws.send(JSON.stringify({ type: 'set_question', question: currentQ.text }));

        faceCaptureTimeoutRef.current = window.setTimeout(() => {
          if (videoRef.current && videoRef.current.videoWidth > 0) {
            const canvas = document.createElement('canvas');
            canvas.width  = videoRef.current.videoWidth;
            canvas.height = videoRef.current.videoHeight;
            canvas.getContext('2d')?.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
            try {
              if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'face_image', image: canvas.toDataURL('image/jpeg', 0.8) }));
              }
            } catch {
              setSystemStatus('Connection interrupted');
            }
          }
        }, 2000);
      };

      ws.onmessage = event => {
        if (typeof event.data !== 'string') return;
        let payload: Record<string, any>;
        try {
          payload = JSON.parse(event.data);
        } catch {
          setSystemStatus('Received malformed server response');
          return;
        }
        if (payload.type === 'status' && typeof payload.message === 'string') {
          setSystemStatus(payload.message);
        }
        else if (payload.type === 'transcript_partial' && typeof payload.text === 'string') {
          setTranscript(payload.text);
          // Only update answers if there's actually text to avoid clearing it during the "reset" signal
          // unless we want it to clear. In this case, if the backend sends empty, we should clear it.
          setAnswers(prev => {
            const newAnswers = [...prev];
            newAnswers[activeQIndexRef.current] = payload.text;
            return newAnswers;
          });
        }
        else if (payload.type === 'transcript' && typeof payload.text === 'string') {
          setTranscript(payload.text);
          setAnswers(prev => {
            const newAnswers = [...prev];
            newAnswers[activeQIndexRef.current] = payload.text;
            return newAnswers;
          });
        }
        else if (payload.type === 'risk_result') {
          if (payload.extracted_fields && typeof payload.extracted_fields === 'object') {
            setExtractedData(prev => ({ ...prev, ...payload.extracted_fields }));
          }
          if (payload.summary && typeof payload.summary === 'object') {
            setSessionSummary(payload.summary as SessionSummary);
          }
          if (payload.data && typeof payload.data === 'object') {
            setRiskResult(payload.data as RiskResult);
          }
        }
        else if (payload.type === 'advance_question') {
          if (activeQIndexRef.current === INTERVIEW_QUESTIONS.length - 1) {
            setIsFinished(true);
            endSession();
          } else {
            setActiveQIndex(prev => prev + 1);
            setTranscript('');
          }
        }
      };

      ws.onerror = () => {
        setSystemStatus('Connection error');
      };

      ws.onclose = () => {
        const recorder = mediaRecorderRef.current;
        if (recorder && recorder.state !== 'inactive') {
          try {
            recorder.stop();
          } catch {
            // Ignore recorder shutdown errors on close.
          }
        }
        if (videoRef.current?.srcObject) {
          (videoRef.current.srcObject as MediaStream).getTracks().forEach(t => t.stop());
          videoRef.current.srcObject = null;
        }
        setIsConnected(false);
        setIsStarting(false);
        setSystemStatus('Session ended');
      };
    } catch (err) {
      console.error(err);
      setSystemStatus('Camera access denied');
      setIsStarting(false);
    }
  }, [currentQ, isConnected, isStarting]);

  const endSession = useCallback(() => {
    if (faceCaptureTimeoutRef.current) {
      window.clearTimeout(faceCaptureTimeoutRef.current);
      faceCaptureTimeoutRef.current = null;
    }
    
    // Stop PCM capture
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }

    wsRef.current?.close();
    if (videoRef.current?.srcObject)
      (videoRef.current.srcObject as MediaStream).getTracks().forEach(t => t.stop());
    wsRef.current = null;
    setIsConnected(false);
    setIsStarting(false);
    setSystemStatus('Session ended');
  }, []);

  useEffect(() => {
    return () => {
      endSession();
    };
  }, [endSession]);

  const resetSession = useCallback(() => {
    endSession();
    setActiveQIndex(0);
    setAnswers(new Array(INTERVIEW_QUESTIONS.length).fill(''));
    setTranscript('');
    setExtractedData({});
    setRiskResult(null);
    setSessionSummary(null);
    setIsFinished(false);
  }, [endSession]);

  const toggleMic = useCallback(() => {
    (videoRef.current?.srcObject as MediaStream | null)?.getAudioTracks().forEach(t => { t.enabled = !t.enabled; });
    setIsMicOn(p => !p);
  }, []);

  const toggleVideo = useCallback(() => {
    (videoRef.current?.srcObject as MediaStream | null)?.getVideoTracks().forEach(t => { t.enabled = !t.enabled; });
    setIsVideoOn(p => !p);
  }, []);

  if (isFinished) {
    return (
      <InterviewResults
        questions={INTERVIEW_QUESTIONS}
        answers={answers}
        riskResult={riskResult}
        sessionSummary={sessionSummary}
        onReset={resetSession}
      />
    );
  }

  if (!hasQuestions || !currentQ) {
    return (
      <div style={{ height: '100dvh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#080A0E', color: '#F1F5F9' }}>
        No interview questions configured. Add entries in frontend/lib/questions.ts.
      </div>
    );
  }

  // Helper: icon button style
  const iconBtn = (danger = false, active = true) => ({
    width: 44, height: 44, borderRadius: '50%',
    border: active ? (danger ? '1px solid rgba(239,68,68,0.25)' : '1px solid rgba(255,255,255,0.10)') : '1px solid rgba(239,68,68,0.25)',
    background: active ? (danger ? 'rgba(239,68,68,0.10)' : 'rgba(255,255,255,0.06)') : 'rgba(239,68,68,0.15)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    cursor: 'pointer', transition: 'all 0.2s ease', flexShrink: 0,
  });

  return (
    <div style={{ height: '100dvh', display: 'flex', flexDirection: 'column', background: '#080A0E', overflow: 'hidden', fontFamily: 'var(--font-geist-sans), system-ui, sans-serif', color: '#F1F5F9' }}>

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header style={{ height: 56, borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 16px', background: '#080A0E', flexShrink: 0, gap: 12 }}>
        {/* Left: menu (mobile) + brand */}
        <div className="flex items-center gap-3">
          {isConnected && (
            <button aria-label="Open section navigation" className="lg:hidden flex items-center justify-center rounded-lg" onClick={() => setShowSectionNav(true)}
              style={{ width: 36, height: 36, background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.08)', cursor: 'pointer' }}>
              <Menu size={16} color="#94A3B8" />
            </button>
          )}
          <div className="flex items-center gap-2 lg:hidden">
            <ShieldCheck size={15} color="#3B6FD4" />
            <span className="text-sm font-semibold" style={{ color: '#F1F5F9' }}>LoanAI</span>
          </div>
        </div>

        {/* Center: status */}
        <div className="flex items-center gap-2" style={{ flex: 1, justifyContent: 'center' }}>
          <div className={isConnected ? 'animate-pulse-dot status-dot' : 'status-dot'}
            style={{ background: isConnected ? '#3B6FD4' : '#374151' }} />
          <span className="text-xs font-medium" style={{ color: isConnected ? '#94A3B8' : '#64748B' }}>{systemStatus}</span>
        </div>

        {/* Right: session ID (desktop only) */}
        <div className="flex items-center gap-2">
          <span className="hidden sm:block text-xs font-mono" style={{ color: '#374151' }}>
            {sessionId}
          </span>
        </div>
      </header>

      {/* ── Body ───────────────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">

        {/* Desktop left sidebar */}
        <SectionNav sections={SECTIONS} currentSection={currentQ.section} activeQIndex={activeQIndex} totalQ={INTERVIEW_QUESTIONS.length} />

        {/* Center */}
        <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', padding: '12px', gap: 10 }}>
          {/* Video */}
          <div style={{ flex: 1, position: 'relative', borderRadius: 16, overflow: 'hidden', background: '#0A0D12', border: '1px solid rgba(255,255,255,0.07)', boxShadow: '0 0 0 1px rgba(0,0,0,0.4), 0 24px 64px rgba(0,0,0,0.6)', minHeight: 0 }}>
            <video ref={videoRef} autoPlay muted playsInline
              style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', opacity: isVideoOn ? 0.85 : 0, transition: 'opacity 0.4s ease' }} />

            {/* Video off */}
            {!isVideoOn && isConnected && (
              <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0A0D12' }}>
                <div style={{ width: 56, height: 56, borderRadius: '50%', background: 'rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <VideoOff size={22} color="#64748B" />
                </div>
              </div>
            )}

            {/* Pre-start CTA */}
            {!isConnected && (
              <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 20, background: 'linear-gradient(135deg, #080A0E 0%, #0F1218 100%)', padding: 24 }}>
                <button aria-label="Start interview session" disabled={isStarting} onClick={startSession} style={{ width: 80, height: 80, borderRadius: '50%', background: 'rgba(59,111,212,0.12)', border: '1px solid rgba(59,111,212,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: isStarting ? 'not-allowed' : 'pointer', transition: 'all 0.25s ease', opacity: isStarting ? 0.7 : 1 }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(59,111,212,0.22)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(59,111,212,0.12)'; }}>
                  <Video size={28} color="#3B6FD4" />
                </button>
                <div style={{ textAlign: 'center' }}>
                  <p style={{ fontSize: 16, fontWeight: 500, color: '#F1F5F9', marginBottom: 6 }}>{isStarting ? 'Connecting session...' : 'Start your loan assessment'}</p>
                  <p style={{ fontSize: 13, color: '#64748B' }}>Camera and microphone required · Encrypted</p>
                </div>
              </div>
            )}

            {/* Question overlay */}
            <AnimatePresence mode="wait">
              {isConnected && (
                <motion.div key={currentQ.id} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.4, ease: [0.16,1,0.3,1] }}
                  style={{ position: 'absolute', bottom: 14, left: 14, right: 14, padding: '16px 18px', borderRadius: 12, background: 'rgba(8,10,14,0.84)', backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)', border: '1px solid rgba(255,255,255,0.08)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8, flexWrap: 'wrap' }}>
                    <span style={{ fontSize: 11, fontWeight: 600, color: '#64748B', letterSpacing: '0.07em', textTransform: 'uppercase', fontFamily: 'var(--font-geist-mono)' }}>
                      Q{activeQIndex + 1}/{INTERVIEW_QUESTIONS.length}
                    </span>
                    <span style={{ width: 3, height: 3, borderRadius: '50%', background: '#374151', display: 'inline-block' }} />
                    <span className="truncate" style={{ fontSize: 11, fontWeight: 500, color: '#64748B', maxWidth: 160 }}>{currentQ.section}</span>
                    <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
                      {currentQ.tags.slice(0, 2).map(tag => (
                        <span key={tag} className="tag-pill">{tag}</span>
                      ))}
                    </div>
                  </div>
                  <p style={{ fontSize: 15, fontWeight: 300, color: '#F1F5F9', lineHeight: 1.55, margin: 0 }}>{currentQ.text}</p>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Recording badge */}
            {isConnected && (
              <div style={{ position: 'absolute', top: 12, right: 12, display: 'flex', alignItems: 'center', gap: 6, padding: '5px 10px', borderRadius: 999, background: 'rgba(8,10,14,0.78)', backdropFilter: 'blur(12px)', border: '1px solid rgba(255,255,255,0.08)' }}>
                <div className="animate-pulse-dot status-dot" style={{ background: '#10B981' }} />
                <span style={{ fontSize: 11, fontWeight: 500, color: '#10B981', letterSpacing: '0.04em' }}>REC</span>
              </div>
            )}
          </div>

          {/* Transcript */}
          {isConnected && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: 0.1 }}
              style={{ borderRadius: 12, border: '1px solid rgba(255,255,255,0.06)', background: '#0F1218', padding: '12px 16px', flexShrink: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <Mic size={11} color="#3B6FD4" />
                <span style={{ fontSize: 10, fontWeight: 600, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.07em' }}>Live Transcript</span>
                <div className="animate-pulse-dot status-dot ml-auto" style={{ background: '#3B6FD4' }} />
              </div>
              <p style={{ fontSize: 13, fontWeight: 300, color: transcript ? '#94A3B8' : '#374151', lineHeight: 1.6, margin: 0, fontStyle: transcript ? 'italic' : 'normal' }}>
                {transcript || 'Listening for speech...'}
              </p>
            </motion.div>
          )}

          {/* Controls */}
          {isConnected && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, flexShrink: 0, flexWrap: 'wrap' }}>
              <button aria-label="Toggle microphone" aria-pressed={isMicOn} onClick={toggleMic} title="Toggle mic" style={iconBtn(false, isMicOn)}>
                {isMicOn ? <Mic size={16} color="#94A3B8" /> : <MicOff size={16} color="#EF4444" />}
              </button>
              <button aria-label="Toggle camera" aria-pressed={isVideoOn} onClick={toggleVideo} title="Toggle camera" style={iconBtn(false, isVideoOn)}>
                {isVideoOn ? <Video size={16} color="#94A3B8" /> : <VideoOff size={16} color="#EF4444" />}
              </button>
              <button
                disabled={!transcript.trim()}
                onClick={() => {
                  // Capture current transcript as the final answer for this question
                  const currentText = transcript.trim();
                  setAnswers(prev => {
                    const newAnswers = [...prev];
                    newAnswers[activeQIndex] = currentText;
                    return newAnswers;
                  });

                  if (activeQIndex === INTERVIEW_QUESTIONS.length - 1) {
                    setIsFinished(true);
                    endSession();
                  } else {
                    // Send signal to backend to clear buffer for new question
                    if (wsRef.current?.readyState === WebSocket.OPEN) {
                      wsRef.current.send(JSON.stringify({ type: 'clear_buffer' }));
                    }
                    setActiveQIndex(p => p + 1);
                    setTranscript('');
                  }
                }}
                style={{
                  height: 44,
                  padding: '0 16px',
                  borderRadius: 999,
                  border: transcript.trim() ? '1px solid rgba(59,111,212,0.30)' : '1px solid rgba(255,255,255,0.05)',
                  background: transcript.trim() ? 'rgba(59,111,212,0.10)' : 'rgba(255,255,255,0.02)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  cursor: transcript.trim() ? 'pointer' : 'not-allowed',
                  color: transcript.trim() ? '#93C5FD' : '#374151',
                  fontSize: 13,
                  fontWeight: 500,
                  transition: 'all 0.2s ease',
                  opacity: transcript.trim() ? 1 : 0.5,
                }}>
                {activeQIndex === INTERVIEW_QUESTIONS.length - 1 ? 'Finish' : 'Next'}
                <ChevronRight size={13} color={transcript.trim() ? '#93C5FD' : '#374151'} />
              </button>
              <button aria-label="End session" onClick={endSession} title="End session" style={iconBtn(true, false)}>
                <PhoneOff size={16} color="#EF4444" />
              </button>
            </div>
          )}

          {/* Progress bar */}
          {isConnected && (
            <div style={{ flexShrink: 0, height: 2, background: 'rgba(255,255,255,0.05)', borderRadius: 999, overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${progressPct}%`, background: 'linear-gradient(90deg, #3B6FD4, #60A5FA)', borderRadius: 999, transition: 'width 0.6s cubic-bezier(0.16,1,0.3,1)', boxShadow: '0 0 8px rgba(59,111,212,0.4)' }} />
            </div>
          )}
        </main>
      </div>

      {/* ── Mobile sheets ──────────────────────────────────────────────── */}
      <MobileSectionSheet
        open={showSectionNav}
        onClose={() => setShowSectionNav(false)}
        sections={SECTIONS}
        currentSection={currentQ.section}
        activeQIndex={activeQIndex}
        totalQ={INTERVIEW_QUESTIONS.length}
      />
    </div>
  );
}
