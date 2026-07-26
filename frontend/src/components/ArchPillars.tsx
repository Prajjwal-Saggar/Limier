"use client";

import { motion } from "framer-motion";
import { ShieldCheck, GitBranch, Brain, Sparkles, ArrowDown } from "lucide-react";

interface ArchPillarsProps {
  onRunDemo: () => void;
}

const pillars = [
  {
    icon: "GitBranch",
    label: "Rules Engine",
    sublabel: "Deterministic",
    description: "Hard-coded typology rules for structuring, rapid cash-out, and round-trip patterns. Guaranteed safety net - overrides ML if a known typology fires.",
    colorClass: "text-sky-400",
    borderClass: "border-sky-400/20",
    bgClass: "bg-sky-400/5",
  },
  {
    icon: "Brain",
    label: "Isolation Forest",
    sublabel: "Unsupervised",
    description: "Detects statistical outliers across 28 behavioral and cash-flow features. Platt-calibrated to output true P(fraud) probabilities.",
    colorClass: "text-violet-400",
    borderClass: "border-violet-400/20",
    bgClass: "bg-violet-400/5",
  },
  {
    icon: "ShieldCheck",
    label: "XGBoost + SHAP",
    sublabel: "Supervised",
    description: "Gradient-boosted classifier with scale_pos_weight for 0.15% fraud rate. SHAP provides per-transaction explainability for every SAR.",
    colorClass: "text-emerald-400",
    borderClass: "border-emerald-400/20",
    bgClass: "bg-emerald-400/5",
  },
];

const iconMap: Record<string, React.ReactNode> = {
  GitBranch: <GitBranch className="w-6 h-6" />,
  Brain: <Brain className="w-6 h-6" />,
  ShieldCheck: <ShieldCheck className="w-6 h-6" />,
};

export function ArchPillars({ onRunDemo }: ArchPillarsProps) {
  return (
    <section className="relative min-h-screen flex flex-col justify-center pt-24 pb-16 overflow-hidden">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] bg-primary/4 rounded-full blur-3xl" />
      </div>
      <div className="relative max-w-7xl mx-auto px-6 w-full">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="flex items-center gap-2 mb-6">
          <div className="h-px flex-1 max-w-16 bg-gradient-to-r from-transparent to-primary/40" />
          <span className="text-primary text-xs font-mono uppercase tracking-widest">AML Detection Platform</span>
          <div className="h-px flex-1 max-w-16 bg-gradient-to-l from-transparent to-primary/40" />
        </motion.div>
        
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.1 }} className="mb-6 max-w-4xl">
          <h1 className="text-5xl md:text-6xl lg:text-7xl tracking-tight text-foreground leading-none mb-4">
            Catch money laundering<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary via-emerald-400 to-sky-400">before it hides.</span>
          </h1>
          <p className="text-muted-foreground text-lg max-w-2xl leading-relaxed">Three detection pillars fused into a single calibrated risk score. Natural language investigation powered by Llama 3.</p>
        </motion.div>
        
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.2 }} className="flex flex-wrap items-center gap-4 mb-16">
          <button
            id="run-demo-btn"
            onClick={onRunDemo}
            aria-label="Run a pre-loaded demo investigation"
            className="group relative flex items-center gap-2 px-6 py-3 bg-primary text-black font-semibold rounded-xl hover:bg-emerald-400 transition-all duration-200 shadow-[0_0_24px_rgba(34,197,94,0.25)]"
          >
            <Sparkles className="w-4 h-4" />
            Run Demo Investigation
          </button>
          <a href="#dashboard" className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground text-sm transition-colors duration-200">
            <ArrowDown className="w-4 h-4" />
            Skip to dashboard
          </a>
        </motion.div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {pillars.map((pillar, i) => (
            <motion.div
              key={pillar.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 + i * 0.08 }}
              className={`relative rounded-2xl border ${pillar.borderClass} ${pillar.bgClass} p-6 backdrop-blur-sm`}
            >
              <div className="absolute top-4 right-4 text-xs text-muted-foreground/30 font-mono">{String(i + 1).padStart(2, "0")}</div>
              <div className={`w-10 h-10 rounded-xl ${pillar.bgClass} border ${pillar.borderClass} flex items-center justify-center ${pillar.colorClass} mb-4`}>
                {iconMap[pillar.icon]}
              </div>
              <span className={`text-xs font-mono uppercase tracking-wider ${pillar.colorClass}`}>{pillar.sublabel}</span>
              <h3 className="text-lg font-semibold text-foreground mt-1 mb-2">{pillar.label}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{pillar.description}</p>
            </motion.div>
          ))}
        </div>
        
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5, delay: 0.6 }} className="mt-4 flex items-center gap-3">
          <div className="h-px flex-1 bg-gradient-to-r from-sky-400/20 via-violet-400/20 to-primary/20" />
          <span className="text-xs text-muted-foreground/40 font-mono tracking-wider">FUSED VIA PLATT-CALIBRATED META-ENSEMBLE</span>
          <div className="h-px flex-1 bg-gradient-to-l from-sky-400/20 via-violet-400/20 to-primary/20" />
        </motion.div>
      </div>
      
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }} className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center">
        <div className="w-5 h-8 rounded-full border border-white/10 flex items-start justify-center pt-1">
          <motion.div animate={{ y: [0, 10, 0] }} transition={{ duration: 1.5, repeat: Infinity }} className="w-1 h-2 bg-primary/40 rounded-full" />
        </div>
      </motion.div>
    </section>
  );
}
