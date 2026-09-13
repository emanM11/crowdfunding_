import { motion } from "framer-motion";

export default function Reveal({ children, className = "", as: Tag = "div", delay = 0 }) {
  const Component = motion[Tag] || motion.div;
  return (
    <Component
      className={className}
      initial={{ opacity: 0, y: 26 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.12 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1], delay }}
    >
      {children}
    </Component>
  );
}