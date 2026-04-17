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
import { INTERVIEW_QUESTIONS } from '../lib/questions';
import { ScoreRing } from './ui/score-ring';

// ─── Types ────────────────────────────────────────────────────────────────────
type RiskResult = {
  decision: 'APPROVE' | 'DECLINE' | 'REVIEW';
  risk_score: number;
  risk_band: string;
  top_factors: string[];
  flags: string[];
  llm_explanation: string;
};

type ExtractedData = {
  monthly_income?: number;
  employment_tenure_months?: number;
  employment_type?: string;
  amount?: number;
  existing_emis?: number;
  age?: number;
};

// ─── Constants ────────────────────────────────────────────────────────────────
const SECTIONS = Array.from(new Set(INTERVIEW_QUESTIONS.map(q => q.section)));

const DECISION_CONFIG = {
  APPROVE: { label: 'Approved',     color: '#10B981', bg: 'rgba(16,185,129,0.08)',  border: 'rgba(16,185,129,0.20)' },
  DECLINE: { label: 'Declined',     color: '#EF4444', bg: 'rgba(239,68,68,0.08)',   border: 'rgba(239,68,68,0.20)'  },
  REVIEW:  { label: 'Under Review', color: '#F59E0B', bg: 'rgba(245,158,11,0.08)',  border: 'rgba(245,158,11,0.20)' },
};

function formatCurrency(v: number) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency', currency: 'INR', maximumFractionDigits: 0,
  }).format(v);
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

// ─── AnalyticsContent (shared between sidebar and mobile sheet) ────────────────
function AnalyticsContent({
  extractedData, riskResult, isConnected,
}: {
  extractedData: ExtractedData; riskResult: RiskResult | null; isConnected: boolean;
}) {
  const fields = [
    { label: 'Monthly Income', value: extractedData.monthly_income           ? formatCurrency(extractedData.monthly_income)         : null, icon: Banknote  },
    { label: 'Employment',     value: extractedData.employment_type                                                                  ?? null, icon: Briefcase  },
    { label: 'Tenure',         value: extractedData.employment_tenure_months  ? `${extractedData.employment_tenure_months} months`   : null, icon: Clock      },
    { label: 'Loan Amount',    value: extractedData.amount                    ? formatCurrency(extractedData.amount)                 : null, icon: TrendingUp },
    { label: 'Existing EMI',   value: extractedData.existing_emis             ? formatCurrency(extractedData.existing_emis)          : null, icon: CreditCard },
    { label: 'Age',            value: extractedData.age                       ? `${extractedData.age} yrs`                          : null, icon: User       },
  ];

  const decisionCfg = riskResult ? (DECISION_CONFIG[riskResult.decision] ?? DECISION_CONFIG.REVIEW) : null;
  const activeFlags = riskResult?.flags?.filter(f => f !== 'NONE') ?? [];

  return (
    <div className="flex flex-col gap-4">
      {/* Live header */}
      <div className="flex items-center gap-2">
        <Activity size={13} color="#64748B" />
        <span className="text-xs font-semibold uppercase tracking-widest" style={{ color: '#64748B' }}>Live Extraction</span>
        {isConnected && (
          <div className="ml-auto flex items-center gap-1.5">
            <div className="animate-pulse-dot status-dot" style={{ background: '#3B6FD4' }} />
            <span className="text-xs" style={{ color: '#3B6FD4' }}>Live</span>
          </div>
        )}
      </div>

      {/* Fields grid */}
      <div className="rounded-xl p-4" style={{ background: '#0F1218', border: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="grid grid-cols-2 gap-4">
          {fields.map(({ label, value, icon: Icon }) => (
            <div key={label}>
              <div className="flex items-center gap-1.5 mb-1">
                <Icon size={11} color="#64748B" />
                <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: '#64748B' }}>{label}</p>
              </div>
              <AnimatePresence mode="wait">
                <motion.p key={value ?? 'empty'} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.25 }}
                  className="font-mono text-sm leading-none" style={{ color: value ? '#F1F5F9' : '#374151' }}>
                  {value ?? '—'}
                </motion.p>
              </AnimatePresence>
            </div>
          ))}
        </div>
      </div>

      {/* Risk result */}
      <AnimatePresence>
        {riskResult && decisionCfg && (
          <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: [0.16,1,0.3,1] }}
            className="rounded-xl overflow-hidden" style={{ border: `1px solid ${decisionCfg.border}`, background: decisionCfg.bg }}>
            <div className="flex items-center justify-between px-5 pt-5 pb-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-widest mb-1.5" style={{ color: '#64748B' }}>Risk Decision</p>
                <h3 className="text-2xl font-bold tracking-tight" style={{ color: decisionCfg.color }}>{decisionCfg.label}</h3>
                <p className="text-xs mt-1 font-mono" style={{ color: '#64748B' }}>Band: {riskResult.risk_band}</p>
              </div>
              <ScoreRing score={riskResult.risk_score} decision={riskResult.decision} size={84} strokeWidth={6} />
            </div>

            <div style={{ height: 1, background: 'rgba(255,255,255,0.06)' }} />
            <div className="px-5 pt-4 pb-5 space-y-4">
              {riskResult.top_factors?.length > 0 && (
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-widest mb-2" style={{ color: '#64748B' }}>Key Factors</p>
                  <div className="flex flex-col gap-1.5">
                    {riskResult.top_factors.map(f => (
                      <div key={f} className="flex items-center gap-2">
                        <ChevronRight size={10} color="#3B6FD4" />
                        <span className="text-xs leading-snug" style={{ color: '#94A3B8' }}>{f}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {activeFlags.length > 0 && (
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-widest mb-2" style={{ color: '#EF4444', opacity: 0.7 }}>Risk Flags</p>
                  <div className="flex flex-col gap-1.5">
                    {activeFlags.map(flag => (
                      <div key={flag} className="flex items-center gap-2">
                        <AlertCircle size={11} color="#EF4444" />
                        <span className="text-xs leading-snug" style={{ color: '#FDA5A5' }}>{flag}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {riskResult.llm_explanation && (
                <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: 12 }}>
                  <p className="text-[10px] font-semibold uppercase tracking-widest mb-1.5" style={{ color: '#64748B' }}>AI Reasoning</p>
                  <p className="text-xs leading-relaxed" style={{ color: '#94A3B8' }}>{riskResult.llm_explanation}</p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {!riskResult && (
        <div className="rounded-xl flex flex-col items-center justify-center py-8 gap-3"
          style={{ border: '1px solid rgba(255,255,255,0.06)', background: '#0F1218' }}>
          <div className="rounded-full flex items-center justify-center"
            style={{ width: 40, height: 40, background: 'rgba(59,111,212,0.10)', border: '1px solid rgba(59,111,212,0.15)' }}>
            <TrendingUp size={18} color="#3B6FD4" />
          </div>
          <div className="text-center">
            <p className="text-sm font-medium" style={{ color: '#64748B' }}>Awaiting assessment</p>
            <p className="text-xs mt-0.5" style={{ color: '#374151' }}>Risk score appears as you answer</p>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Desktop right sidebar ────────────────────────────────────────────────────
function AnalyticsPanel(props: { extractedData: ExtractedData; riskResult: RiskResult | null; isConnected: boolean }) {
  return (
    <aside className="hidden xl:flex flex-col border-l overflow-y-auto"
      style={{ width: 312, minWidth: 312, background: '#0A0D12', borderColor: 'rgba(255,255,255,0.06)', padding: '24px 16px', gap: 20 }}>
      <AnalyticsContent {...props} />
    </aside>
  );
}

// ─── Mobile bottom sheet ──────────────────────────────────────────────────────
function MobileAnalyticsSheet({
  open, onClose, ...props
}: { open: boolean; onClose: () => void; extractedData: ExtractedData; riskResult: RiskResult | null; isConnected: boolean }) {
  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={onClose}
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)', zIndex: 40 }}
          />
          {/* Sheet */}
          <motion.div
            key="sheet"
            initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 32, stiffness: 340, mass: 0.9 }}
            style={{
              position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 50,
              background: '#0F1218', borderTop: '1px solid rgba(255,255,255,0.10)',
              borderRadius: '20px 20px 0 0',
              maxHeight: '80dvh', overflowY: 'auto',
              padding: '0 16px 32px',
            }}
          >
            {/* Handle */}
            <div className="flex items-center justify-center pt-3 pb-4">
              <div style={{ width: 36, height: 4, borderRadius: 99, background: 'rgba(255,255,255,0.12)' }} />
            </div>
            {/* Close */}
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm font-semibold" style={{ color: '#F1F5F9' }}>Live Analytics</span>
              <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4 }}>
                <X size={18} color="#64748B" />
              </button>
            </div>
            <AnalyticsContent {...props} />
          </motion.div>
        </>
      )}
    </AnimatePresence>
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
              <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4 }}>
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
                  <div key={sec} onClick={onClose} className="flex items-start gap-3 rounded-lg px-3 py-2.5"
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
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

// ─── Main Component ────────────────────────────────────────────────────────────
export default function InterviewScreen() {
  const videoRef         = useRef<HTMLVideoElement>(null);
  const wsRef            = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);

  const [isConnected, setIsConnected]         = useState(false);
  const [isMicOn, setIsMicOn]                 = useState(true);
  const [isVideoOn, setIsVideoOn]             = useState(true);
  const [transcript, setTranscript]           = useState('');
  const [activeQIndex, setActiveQIndex]       = useState(0);
  const [extractedData, setExtractedData]     = useState<ExtractedData>({});
  const [riskResult, setRiskResult]           = useState<RiskResult | null>(null);
  const [systemStatus, setSystemStatus]       = useState('Ready to begin');
  const [sessionId, setSessionId]             = useState('');
  const [showAnalytics, setShowAnalytics]     = useState(false);
  const [showSectionNav, setShowSectionNav]   = useState(false);

  useEffect(() => {
    const d = new Date();
    const pad = (n: number) => String(n).padStart(2, '0');
    setSessionId(`${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} · ${String(Math.floor(Math.random()*90000+10000))}`);
  }, []);

  const currentQ    = INTERVIEW_QUESTIONS[activeQIndex];
  const progressPct = ((activeQIndex + 1) / INTERVIEW_QUESTIONS.length) * 100;

  useEffect(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'set_question', question: currentQ.text }));
    }
  }, [activeQIndex, currentQ.text]);

  const startSession = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      if (videoRef.current) videoRef.current.srcObject = stream;

      setSystemStatus('Connecting...');
      const ws = new WebSocket('ws://localhost:8000/ws/audio');
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setSystemStatus('AI Model loading...');

        const audioStream = new MediaStream(stream.getAudioTracks());
        let recorder: MediaRecorder;
        try { recorder = new MediaRecorder(audioStream, { mimeType: 'audio/webm;codecs=opus' }); }
        catch { recorder = new MediaRecorder(audioStream); }
        mediaRecorderRef.current = recorder;

        ws.send(JSON.stringify({ type: 'set_question', question: INTERVIEW_QUESTIONS[0].text }));

        setTimeout(() => {
          if (videoRef.current && videoRef.current.videoWidth > 0) {
            const canvas = document.createElement('canvas');
            canvas.width  = videoRef.current.videoWidth;
            canvas.height = videoRef.current.videoHeight;
            canvas.getContext('2d')?.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
            ws.send(JSON.stringify({ type: 'face_image', image: canvas.toDataURL('image/jpeg', 0.8) }));
          }
        }, 2000);

        recorder.ondataavailable = e => {
          if (e.data?.size > 0 && ws.readyState === WebSocket.OPEN) ws.send(e.data);
        };
        recorder.start(1000);
      };

      ws.onmessage = event => {
        const payload = JSON.parse(event.data);
        if      (payload.type === 'status')        setSystemStatus(payload.message);
        else if (payload.type === 'transcript')    setTranscript(payload.text);
        else if (payload.type === 'risk_result') {
          setExtractedData(prev => ({ ...prev, ...payload.extracted_fields }));
          setRiskResult(payload.data);
        }
        else if (payload.type === 'advance_question')
          setActiveQIndex(prev => Math.min(INTERVIEW_QUESTIONS.length - 1, prev + 1));
      };

      ws.onclose = () => { setIsConnected(false); setSystemStatus('Session ended'); };
    } catch (err) {
      console.error(err);
      setSystemStatus('Camera access denied');
    }
  }, []);

  const endSession = useCallback(() => {
    mediaRecorderRef.current?.stop();
    wsRef.current?.close();
    if (videoRef.current?.srcObject)
      (videoRef.current.srcObject as MediaStream).getTracks().forEach(t => t.stop());
    setIsConnected(false);
    setSystemStatus('Session ended');
  }, []);

  const toggleMic = useCallback(() => {
    (videoRef.current?.srcObject as MediaStream | null)?.getAudioTracks().forEach(t => { t.enabled = !t.enabled; });
    setIsMicOn(p => !p);
  }, []);

  const toggleVideo = useCallback(() => {
    (videoRef.current?.srcObject as MediaStream | null)?.getVideoTracks().forEach(t => { t.enabled = !t.enabled; });
    setIsVideoOn(p => !p);
  }, []);

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
            <button className="lg:hidden flex items-center justify-center rounded-lg" onClick={() => setShowSectionNav(true)}
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

        {/* Right: analytics toggle (mobile) + session ID */}
        <div className="flex items-center gap-2">
          {isConnected && (
            <button className="xl:hidden flex items-center gap-1.5 rounded-lg px-3" onClick={() => setShowAnalytics(true)}
              style={{ height: 36, background: 'rgba(59,111,212,0.12)', border: '1px solid rgba(59,111,212,0.25)', cursor: 'pointer' }}>
              <BarChart2 size={14} color="#3B6FD4" />
              <span className="text-xs font-medium" style={{ color: '#93C5FD' }}>
                {riskResult ? riskResult.risk_score : 'Score'}
              </span>
            </button>
          )}
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
                <button onClick={startSession} style={{ width: 80, height: 80, borderRadius: '50%', background: 'rgba(59,111,212,0.12)', border: '1px solid rgba(59,111,212,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', transition: 'all 0.25s ease' }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(59,111,212,0.22)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(59,111,212,0.12)'; }}>
                  <Video size={28} color="#3B6FD4" />
                </button>
                <div style={{ textAlign: 'center' }}>
                  <p style={{ fontSize: 16, fontWeight: 500, color: '#F1F5F9', marginBottom: 6 }}>Start your loan assessment</p>
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
              <button onClick={toggleMic} title="Toggle mic" style={iconBtn(false, isMicOn)}>
                {isMicOn ? <Mic size={16} color="#94A3B8" /> : <MicOff size={16} color="#EF4444" />}
              </button>
              <button onClick={toggleVideo} title="Toggle camera" style={iconBtn(false, isVideoOn)}>
                {isVideoOn ? <Video size={16} color="#94A3B8" /> : <VideoOff size={16} color="#EF4444" />}
              </button>
              <button
                onClick={() => setActiveQIndex(p => Math.min(INTERVIEW_QUESTIONS.length - 1, p + 1))}
                style={{ height: 44, padding: '0 16px', borderRadius: 999, border: '1px solid rgba(59,111,212,0.30)', background: 'rgba(59,111,212,0.10)', display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', color: '#93C5FD', fontSize: 13, fontWeight: 500, transition: 'all 0.2s ease' }}>
                Next
                <ChevronRight size={13} color="#93C5FD" />
              </button>
              <button onClick={endSession} title="End session" style={iconBtn(true, false)}>
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

        {/* Desktop right sidebar */}
        <AnalyticsPanel extractedData={extractedData} riskResult={riskResult} isConnected={isConnected} />
      </div>

      {/* ── Mobile sheets ──────────────────────────────────────────────── */}
      <MobileAnalyticsSheet
        open={showAnalytics}
        onClose={() => setShowAnalytics(false)}
        extractedData={extractedData}
        riskResult={riskResult}
        isConnected={isConnected}
      />
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
