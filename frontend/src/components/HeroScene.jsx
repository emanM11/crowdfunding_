import { lazy, Suspense, useMemo } from "react";
import { motion } from "framer-motion";
import { HeartHandshake, TrendingUp, Users } from "lucide-react";
import { coinAnimation } from "../lib/coinAnimation";

// Keep lottie-web out of the initial bundle: the engine only loads when the
// hero scene needs it, and if parsing ever fails SafeLottie falls back to CSS.
const SafeLottie = lazy(() => import("./SafeLottie"));

function LazyCoin() {
  const { fallback } = useMemo(
    () => ({
      fallback: (
        <span className="coin-fallback" aria-hidden="true" />
      ),
    }),
    []
  );
  return (
    <Suspense fallback={fallback}>
      <SafeLottie src={coinAnimation} />
    </Suspense>
  );
}

export default function HeroScene({ featured, featuredPct }) {
  return (
    <div className="hero-scene" aria-hidden="true">
      <motion.div
        className="hero-ring ring-a"
        animate={{ rotate: 360 }}
        transition={{ duration: 40, repeat: Infinity, ease: "linear" }}
      />
      <motion.div
        className="hero-ring ring-b"
        animate={{ rotate: -360 }}
        transition={{ duration: 55, repeat: Infinity, ease: "linear" }}
      />

      <div className="hero-coin">
        <LazyCoin />
      </div>
      <div className="hero-coin small">
        <LazyCoin />
      </div>
      <div className="hero-coin mid">
        <LazyCoin />
      </div>

      <motion.span
        className="hero-tag t1"
        animate={{ y: [0, -12, 0] }}
        transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
      >
        <HeartHandshake size={16} />
        {featured ? `إنجاز ${featuredPct}%` : "دعم بلا حدود"}
      </motion.span>
      <motion.span
        className="hero-tag t2"
        animate={{ y: [0, 10, 0] }}
        transition={{ duration: 6, repeat: Infinity, ease: "easeInOut", delay: 0.8 }}
      >
        <TrendingUp size={16} />
        تمويل جماعي مصري
      </motion.span>
      <motion.span
        className="hero-tag t3"
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 5.5, repeat: Infinity, ease: "easeInOut", delay: 1.4 }}
      >
        <Users size={16} />
        آلاف المساندين
      </motion.span>
    </div>
  );
}