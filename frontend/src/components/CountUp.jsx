import { useEffect, useRef, useState } from "react";

function prefersReducedMotion() {
  return (
    typeof window !== "undefined" &&
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

function easeOutCubic(t) {
  return 1 - Math.pow(1 - t, 3);
}

export default function CountUp({ value, duration = 1400, separator = true, className = "" }) {
  const start = 0;
  const end = Number(value) || 0;
  const [current, setCurrent] = useState(prefersReducedMotion() ? end : start);
  const raf = useRef(null);

  useEffect(() => {
    if (prefersReducedMotion() || end === current) {
      setCurrent(end);
      return;
    }
    const t0 = performance.now();
    const tick = (now) => {
      const t = Math.min(1, (now - t0) / duration);
      setCurrent(Math.round(easeOutCubic(t) * end));
      if (t < 1) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [end, duration]);

  const formatted = separator ? current.toLocaleString("en-US") : String(current);
  return <span className={className}>{formatted}</span>;
}