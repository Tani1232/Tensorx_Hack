'use client';

import React from 'react';

interface ScoreRingProps {
  score: number;       // 0 – 1000
  maxScore?: number;   // defaults to 1000
  size?: number;       // SVG size in px, defaults to 120
  strokeWidth?: number;
  decision?: 'APPROVE' | 'DECLINE' | 'REVIEW' | string;
}

const DECISION_COLOR: Record<string, string> = {
  APPROVE: '#10B981',
  DECLINE: '#EF4444',
  REVIEW:  '#F59E0B',
};

export function ScoreRing({
  score,
  maxScore = 1000,
  size = 120,
  strokeWidth = 7,
  decision,
}: ScoreRingProps) {
  const center = size / 2;
  const radius = center - strokeWidth - 4;
  // We draw a 270° arc (from 135° to 45° clockwise)
  const circumference = 2 * Math.PI * radius;
  const arcFraction = 0.75; // 270° / 360°
  const arcLength = circumference * arcFraction;
  const pct = Math.min(Math.max(score / maxScore, 0), 1);
  const filled = arcLength * pct;
  const gap = arcLength - filled;
  // Rotate so arc starts at bottom-left (135deg)
  const rotation = 135;

  const color = decision ? (DECISION_COLOR[decision] ?? '#3B6FD4') : '#3B6FD4';

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        fill="none"
        style={{ transform: `rotate(${rotation}deg)` }}
      >
        {/* Track */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          stroke="rgba(255,255,255,0.06)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${arcLength} ${circumference - arcLength}`}
        />
        {/* Progress arc */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${filled} ${gap + (circumference - arcLength)}`}
          style={{
            transition: 'stroke-dasharray 1s cubic-bezier(0.16,1,0.3,1)',
            filter: `drop-shadow(0 0 6px ${color}66)`,
          }}
        />
      </svg>

      {/* Center label */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="font-mono font-semibold leading-none"
          style={{ fontSize: size * 0.22, color: '#F1F5F9' }}
        >
          {score}
        </span>
        <span
          className="font-sans font-medium uppercase tracking-widest"
          style={{ fontSize: size * 0.08, color: '#64748B', marginTop: 4 }}
        >
          / {maxScore}
        </span>
      </div>
    </div>
  );
}
