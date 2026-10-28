import React, { useState, useEffect, useRef } from 'react';
import { useCountUp } from '../../hooks/useCountUp';

export interface DonutSlice {
  label: string;
  value: number;
  color: string;
}

interface SequentialDonutChartProps {
  title: string;
  slices: DonutSlice[];
  total: number;
  size?: number;
  thickness?: number;
  active?: boolean; // triggers the draw-on animation
  animationDuration?: number; // ms, default 650ms
  onAnimationComplete?: () => void;
  resetKey?: any; // re-triggers animation on dataset switch
  emptyMessage?: string;
}

export const SequentialDonutChart: React.FC<SequentialDonutChartProps> = ({
  title,
  slices,
  total,
  size = 130,
  thickness = 22,
  active = true,
  animationDuration = 650,
  onAnimationComplete,
  resetKey,
  emptyMessage = 'No records',
}) => {
  const [progress, setProgress] = useState<number>(0);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const frameRef = useRef<number | null>(null);
  const startTimeRef = useRef<number | null>(null);
  const completedRef = useRef<boolean>(false);

  const r = (size - thickness) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const circumference = 2 * Math.PI * r;

  // Animated center total counter
  const animatedTotal = useCountUp(active ? total : 0, {
    duration: animationDuration,
    decimals: 0,
    resetKey,
  });

  useEffect(() => {
    // Reset state whenever resetKey changes or active is set to false
    if (!active) {
      setProgress(0);
      completedRef.current = false;
      if (frameRef.current !== null) {
        cancelAnimationFrame(frameRef.current);
        frameRef.current = null;
      }
      return;
    }

    const prefersReducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (prefersReducedMotion) {
      setProgress(1);
      if (!completedRef.current) {
        completedRef.current = true;
        onAnimationComplete?.();
      }
      return;
    }

    setProgress(0);
    completedRef.current = false;
    startTimeRef.current = null;

    const easeOutCubic = (t: number): number => 1 - Math.pow(1 - t, 3);

    const animate = (timestamp: number) => {
      if (startTimeRef.current === null) {
        startTimeRef.current = timestamp;
      }

      const elapsed = timestamp - startTimeRef.current;
      const rawProgress = Math.min(elapsed / animationDuration, 1);
      const eased = easeOutCubic(rawProgress);

      setProgress(eased);

      if (rawProgress < 1) {
        frameRef.current = requestAnimationFrame(animate);
      } else {
        setProgress(1);
        frameRef.current = null;
        if (!completedRef.current) {
          completedRef.current = true;
          onAnimationComplete?.();
        }
      }
    };

    frameRef.current = requestAnimationFrame(animate);

    return () => {
      if (frameRef.current !== null) {
        cancelAnimationFrame(frameRef.current);
      }
    };
  }, [active, resetKey, animationDuration]);

  // Calculate slice geometry
  const validSlices = slices.filter((s) => s.value > 0);
  let cumulative = 0;
  const renderedSlices = validSlices.map((slice, index) => {
    const fraction = total > 0 ? slice.value / total : 0;
    // Visible arc length scaled by progress
    const sliceArc = fraction * circumference * progress;
    // Rotation starting position (-90 is top)
    const rotationDeg = 360 * cumulative * progress - 90;
    cumulative += fraction;
    return {
      ...slice,
      index,
      fraction,
      sliceArc,
      rotationDeg,
    };
  });

  // Entrance rotation and scale
  const entranceRotation = -35 * (1 - progress);
  const entranceScale = 0.88 + 0.12 * progress;
  const chartOpacity = active ? Math.min(0.2 + 0.8 * progress, 1) : 0.45;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 12,
        width: '100%',
        minHeight: 250,
      }}
    >
      <div
        style={{
          fontSize: 12,
          fontWeight: 600,
          color: active ? '#896F81' : '#A892A2',
          letterSpacing: '0.04em',
          textTransform: 'uppercase',
          display: 'flex',
          alignItems: 'center',
          gap: 6,
        }}
      >
        <span>{title}</span>
        {active && progress < 1 && (
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: '#C14E83',
              display: 'inline-block',
              animation: 'pulse 1s infinite',
            }}
          />
        )}
      </div>

      <div
        style={{
          position: 'relative',
          width: size,
          height: size,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          style={{
            transform: `rotate(${entranceRotation}deg) scale(${entranceScale})`,
            transformOrigin: 'center center',
            opacity: chartOpacity,
            transition: 'opacity 0.2s ease',
            overflow: 'visible',
          }}
        >
          {/* Subtle background track */}
          <circle
            cx={cx}
            cy={cy}
            r={r}
            fill="none"
            stroke="#F8EBF1"
            strokeWidth={thickness}
          />

          {/* Empty state guide ring when total is 0 */}
          {total === 0 && (
            <circle
              cx={cx}
              cy={cy}
              r={r}
              fill="none"
              stroke="#ECD9E2"
              strokeWidth={Math.max(thickness - 6, 8)}
              strokeDasharray="4 4"
              opacity={0.8}
            />
          )}

          {/* Slices drawn progressively */}
          {renderedSlices.map((slice) => {
            const isHovered = hoveredIndex === slice.index;
            const isOtherHovered = hoveredIndex !== null && hoveredIndex !== slice.index;
            return (
              <circle
                key={slice.label}
                cx={cx}
                cy={cy}
                r={r}
                fill="none"
                stroke={slice.color}
                strokeWidth={isHovered ? thickness + 3 : thickness}
                strokeDasharray={`${Math.max(slice.sliceArc, 0)} ${circumference}`}
                strokeDashoffset={0}
                transform={`rotate(${slice.rotationDeg}, ${cx}, ${cy})`}
                strokeLinecap="butt"
                opacity={isOtherHovered ? 0.35 : 1}
                style={{
                  cursor: 'pointer',
                  transition: 'stroke-width 0.15s ease, opacity 0.15s ease',
                }}
                onMouseEnter={() => setHoveredIndex(slice.index)}
                onMouseLeave={() => setHoveredIndex(null)}
              />
            );
          })}
        </svg>

        {/* Center label with animated counter */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            pointerEvents: 'none',
          }}
        >
          <span
            style={{
              fontSize: total >= 100 ? 22 : 26,
              fontWeight: 400,
              fontFamily: "'DM Serif Display', Georgia, serif",
              color: '#351D31',
              lineHeight: 1,
            }}
          >
            {animatedTotal}
          </span>
          <span
            style={{
              fontSize: 10,
              color: '#A892A2',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              marginTop: 2,
            }}
          >
            {total === 0 ? 'empty' : 'total'}
          </span>
        </div>
      </div>

      {/* Legend with hover highlight */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '6px 14px',
          justifyContent: 'center',
          maxWidth: size + 110,
        }}
      >
        {validSlices.length === 0 ? (
          <span style={{ fontSize: 11, color: '#A892A2', fontStyle: 'italic' }}>
            {emptyMessage}
          </span>
        ) : (
          validSlices.map((s, i) => {
            const isHovered = hoveredIndex === i;
            const pct = total > 0 ? Math.round((s.value / total) * 100) : 0;
            return (
              <div
                key={s.label}
                onMouseEnter={() => setHoveredIndex(i)}
                onMouseLeave={() => setHoveredIndex(null)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 5,
                  cursor: 'pointer',
                  padding: '2px 4px',
                  borderRadius: 4,
                  background: isHovered ? '#FDF0F5' : 'transparent',
                  transition: 'background 0.15s ease',
                }}
              >
                <div
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: s.color,
                    flexShrink: 0,
                  }}
                />
                <span style={{ fontSize: 11, color: isHovered ? '#351D31' : '#896F81' }}>
                  {s.label}{' '}
                  <strong style={{ color: '#351D31', fontWeight: 700 }}>
                    {active ? Math.round(s.value * progress) : s.value}
                  </strong>{' '}
                  <span style={{ fontSize: 9.5, color: '#A892A2' }}>({pct}%)</span>
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

