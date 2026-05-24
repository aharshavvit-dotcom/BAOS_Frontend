/**
 * Custom hook: animated counter (easeOutCubic).
 * Matches the original landing.js counter animation.
 */
'use client';

import { useEffect, useRef, useState } from 'react';

export function useAnimatedCounter(
  target: number,
  duration: number = 2000,
  decimals: number = 0,
  startOnMount: boolean = false
) {
  const [value, setValue] = useState(0);
  const [started, setStarted] = useState(startOnMount);
  const rafRef = useRef<number | null>(null);

  function start() {
    setStarted(true);
  }

  useEffect(() => {
    if (!started) return;

    const startTime = performance.now();

    function update(currentTime: number) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic — matches original landing.js
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(parseFloat((target * eased).toFixed(decimals)));

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(update);
      } else {
        setValue(parseFloat(target.toFixed(decimals)));
      }
    }

    rafRef.current = requestAnimationFrame(update);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [started, target, duration, decimals]);

  return { value, start };
}
