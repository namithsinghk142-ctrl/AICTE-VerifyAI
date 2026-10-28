import React, { useState, useEffect, useRef } from 'react';

interface CountUpOptions {
  duration?: number; // ms, default 750
  decimals?: number; // default 0
  suffix?: string;
  prefix?: string;
  resetKey?: any; // triggers re-animation when changed
}

/**
 * Smooth requestAnimationFrame count-up hook for KPI and chart metrics.
 * Uses cubic ease-out for polished regulatory dashboard aesthetics.
 * Respects prefers-reduced-motion.
 */
export function useCountUp(
  targetValue: number,
  options: CountUpOptions = {}
): string {
  const {
    duration = 750,
    decimals = 0,
    suffix = '',
    prefix = '',
    resetKey,
  } = options;

  const [displayValue, setDisplayValue] = useState<number>(0);
  const frameRef = useRef<number | null>(null);
  const startTimeRef = useRef<number | null>(null);
  const startValueRef = useRef<number>(0);

  useEffect(() => {
    // Check if user prefers reduced motion
    const prefersReducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (prefersReducedMotion || duration <= 0) {
      setDisplayValue(targetValue);
      return;
    }

    // Cancel any ongoing animation
    if (frameRef.current !== null) {
      cancelAnimationFrame(frameRef.current);
    }

    startTimeRef.current = null;
    startValueRef.current = 0; // count up from 0 on load or reset

    const easeOutCubic = (t: number): number => 1 - Math.pow(1 - t, 3);

    const animate = (timestamp: number) => {
      if (startTimeRef.current === null) {
        startTimeRef.current = timestamp;
      }

      const elapsed = timestamp - startTimeRef.current;
      const progress = Math.min(elapsed / duration, 1);
      const easedProgress = easeOutCubic(progress);

      const current =
        startValueRef.current +
        (targetValue - startValueRef.current) * easedProgress;

      setDisplayValue(current);

      if (progress < 1) {
        frameRef.current = requestAnimationFrame(animate);
      } else {
        setDisplayValue(targetValue);
        frameRef.current = null;
      }
    };

    frameRef.current = requestAnimationFrame(animate);

    return () => {
      if (frameRef.current !== null) {
        cancelAnimationFrame(frameRef.current);
      }
    };
  }, [targetValue, duration, resetKey]);

  const formattedNumber =
    decimals > 0
      ? displayValue.toFixed(decimals)
      : Math.round(displayValue).toLocaleString();

  return `${prefix}${formattedNumber}${suffix}`;
}

export const AnimatedNumber: React.FC<{
  value: number;
  duration?: number;
  decimals?: number;
  suffix?: string;
  prefix?: string;
  resetKey?: any;
}> = ({ value, duration = 750, decimals = 0, suffix = '', prefix = '', resetKey }) => {
  const text = useCountUp(value, { duration, decimals, suffix, prefix, resetKey });
  return <span>{text}</span>;
};
