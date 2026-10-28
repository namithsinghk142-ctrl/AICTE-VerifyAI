import React, { useState, useEffect, useRef } from 'react';
import type { DatasetMode } from '../../types';

export interface TrendDataPoint {
  period: string; // e.g. "May", "Jun", "Jul"
  submissions: number;
  label?: string;
}

interface SubmissionTrendChartProps {
  data: TrendDataPoint[];
  mode: DatasetMode;
  resetKey?: any;
  height?: number;
}

export const SubmissionTrendChart: React.FC<SubmissionTrendChartProps> = ({
  data,
  mode,
  resetKey,
  height = 180,
}) => {
  const [progress, setProgress] = useState<number>(0);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const frameRef = useRef<number | null>(null);
  const startTimeRef = useRef<number | null>(null);

  const isReal = mode === 'real';

  useEffect(() => {
    const prefersReducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (prefersReducedMotion) {
      setProgress(1);
      return;
    }

    setProgress(0);
    startTimeRef.current = null;
    const duration = 950; // ms for progressive left-to-right draw

    const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);

    const animate = (timestamp: number) => {
      if (startTimeRef.current === null) startTimeRef.current = timestamp;
      const elapsed = timestamp - startTimeRef.current;
      const p = Math.min(elapsed / duration, 1);
      setProgress(easeOutCubic(p));

      if (p < 1) {
        frameRef.current = requestAnimationFrame(animate);
      } else {
        setProgress(1);
        frameRef.current = null;
      }
    };

    frameRef.current = requestAnimationFrame(animate);

    return () => {
      if (frameRef.current !== null) {
        cancelAnimationFrame(frameRef.current);
      }
    };
  }, [resetKey, mode]);

  // Chart layout dimensions
  const svgWidth = 560;
  const svgHeight = height;
  const padding = { top: 24, right: 30, bottom: 32, left: 45 };
  const innerWidth = svgWidth - padding.left - padding.right;
  const innerHeight = svgHeight - padding.top - padding.bottom;

  const values = data.map((d) => d.submissions);
  const maxVal = Math.max(...values, isReal ? 5 : 10);
  const minVal = 0;
  const range = maxVal - minVal || 1;

  // Grid ticks
  const yTicks = [0, Math.round(maxVal / 2), maxVal];

  // Coordinates calculation
  const points = data.map((d, index) => {
    const xFraction = data.length > 1 ? index / (data.length - 1) : 0.5;
    const x = padding.left + xFraction * innerWidth;
    const yFraction = (d.submissions - minVal) / range;
    const y = padding.top + innerHeight - yFraction * innerHeight;
    return {
      ...d,
      index,
      x,
      y,
      xFraction,
    };
  });

  // SVG path for line
  const linePath = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
    .join(' ');

  // SVG path for area fill (closing to baseline)
  const baselineY = padding.top + innerHeight;
  const areaPath =
    points.length > 0
      ? `${linePath} L ${points[points.length - 1].x} ${baselineY} L ${points[0].x} ${baselineY} Z`
      : '';

  // Approximate line length for stroke-dasharray animation
  let totalLength = 0;
  for (let i = 1; i < points.length; i++) {
    const dx = points[i].x - points[i - 1].x;
    const dy = points[i].y - points[i - 1].y;
    totalLength += Math.sqrt(dx * dx + dy * dy);
  }
  const strokeDash = Math.max(totalLength, 100);
  const strokeOffset = strokeDash * (1 - progress);

  // Clip width for area fill
  const clipWidth = innerWidth * progress + padding.left;

  return (
    <div style={{ width: '100%', position: 'relative' }}>
      <svg
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        style={{ width: '100%', height: 'auto', display: 'block', overflow: 'visible' }}
      >
        <defs>
          {/* Gradient for area fill */}
          <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#C14E83" stopOpacity={0.25} />
            <stop offset="85%" stopColor="#C14E83" stopOpacity={0.02} />
            <stop offset="100%" stopColor="#C14E83" stopOpacity={0} />
          </linearGradient>

          {/* Clip path synchronized with line draw progress */}
          <clipPath id="revealClip">
            <rect
              x="0"
              y="0"
              width={clipWidth}
              height={svgHeight}
            />
          </clipPath>
        </defs>

        {/* Horizontal grid lines & Y labels */}
        {yTicks.map((tick) => {
          const y = padding.top + innerHeight - ((tick - minVal) / range) * innerHeight;
          return (
            <g key={tick}>
              <line
                x1={padding.left}
                y1={y}
                x2={padding.left + innerWidth}
                y2={y}
                stroke="#F3E0E9"
                strokeWidth={1}
                strokeDasharray={tick === 0 ? 'none' : '3 3'}
              />
              <text
                x={padding.left - 10}
                y={y + 3.5}
                textAnchor="end"
                fontSize={10}
                fill="#896F81"
                fontWeight={500}
              >
                {tick}
              </text>
            </g>
          );
        })}

        {/* Area fill beneath line (clipped to draw progress) */}
        {areaPath && (
          <path
            d={areaPath}
            fill="url(#areaGradient)"
            clipPath="url(#revealClip)"
            style={{ opacity: isReal ? 0.2 : 0.95 }}
          />
        )}

        {/* Trend line drawn progressively from left to right */}
        {linePath && (
          <path
            d={linePath}
            fill="none"
            stroke={isReal ? '#A892A2' : '#C14E83'}
            strokeWidth={2.5}
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeDasharray={strokeDash}
            strokeDashoffset={strokeOffset}
          />
        )}

        {/* Data points reveal as the line reaches them */}
        {points.map((p) => {
          const isRevealed = progress >= p.xFraction * 0.92;
          const isHovered = hoveredIndex === p.index;
          return (
            <g
              key={p.period}
              transform={`translate(${p.x}, ${p.y})`}
              style={{
                opacity: isRevealed ? 1 : 0,
                transform: `translate(${p.x}px, ${p.y}px) scale(${isRevealed ? (isHovered ? 1.4 : 1) : 0})`,
                transition: 'opacity 0.2s ease, transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1)',
                cursor: 'pointer',
              }}
              onMouseEnter={() => setHoveredIndex(p.index)}
              onMouseLeave={() => setHoveredIndex(null)}
            >
              {/* Outer halo on hover */}
              {isHovered && (
                <circle
                  r={8}
                  fill="rgba(193, 78, 131, 0.2)"
                />
              )}
              {/* Point circle */}
              <circle
                r={isHovered ? 4.5 : 3.5}
                fill={isReal ? '#896F81' : '#8A2F5B'}
                stroke="#FFFFFF"
                strokeWidth={2}
              />
            </g>
          );
        })}

        {/* X-axis Month Labels */}
        {points.map((p) => (
          <text
            key={p.period}
            x={p.x}
            y={svgHeight - 10}
            textAnchor="middle"
            fontSize={10.5}
            fontWeight={hoveredIndex === p.index ? 700 : 500}
            fill={hoveredIndex === p.index ? '#351D31' : '#896F81'}
            style={{ transition: 'fill 0.15s ease' }}
          >
            {p.period}
          </text>
        ))}
      </svg>

      {/* Floating Tooltip when hovering over a point */}
      {hoveredIndex !== null && points[hoveredIndex] && (
        <div
          style={{
            position: 'absolute',
            left: `${(points[hoveredIndex].x / svgWidth) * 100}%`,
            top: `${(points[hoveredIndex].y / svgHeight) * 100}%`,
            transform: 'translate(-50%, -125%)',
            background: '#351D31',
            color: '#FFFFFF',
            padding: '6px 10px',
            borderRadius: 8,
            fontSize: 11,
            pointerEvents: 'none',
            boxShadow: '0 4px 12px rgba(53, 29, 49, 0.25)',
            whiteSpace: 'nowrap',
            zIndex: 10,
          }}
        >
          <div style={{ fontWeight: 700, fontSize: 11.5 }}>
            {points[hoveredIndex].period}: {points[hoveredIndex].submissions} submissions
          </div>
          <div style={{ fontSize: 9.5, color: '#ECD9E2', marginTop: 1 }}>
            {isReal ? 'Authentic pipeline' : 'Simulated demo filing'}
          </div>
        </div>
      )}

      {/* Real Data Empty / Isolation Explanation Banner */}
      {isReal && (
        <div
          style={{
            marginTop: 8,
            padding: '6px 12px',
            background: '#FFF9FA',
            border: '1px dashed #ECD9E2',
            borderRadius: 8,
            fontSize: 11,
            color: '#896F81',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span>
            ℹ <strong>Zero authentic submissions</strong> filed across active periods. Confidential dossiers isolated.
          </span>
          <span style={{ fontSize: 10, fontWeight: 600, color: '#C14E83' }}>
            Real Data Isolation
          </span>
        </div>
      )}
    </div>
  );
};

