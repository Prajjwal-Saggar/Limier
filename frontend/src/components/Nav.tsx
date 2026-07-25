"use client";

import { HealthStatusPill } from "./HealthStatusPill";

export function Nav() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 glass-panel border-b border-white/5 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {/* Logo element */}
          <div className="w-6 h-6 rounded bg-primary/20 flex items-center justify-center border border-primary/40 shadow-[0_0_12px_rgba(34,197,94,0.1)]">
            <div className="w-2 h-2 bg-primary rounded-full shadow-[0_0_8px_rgba(34,197,94,0.6)]" />
          </div>
          <span className="font-display font-semibold text-xl tracking-tight text-foreground">
            Limier
          </span>
        </div>
        
        <div className="flex items-center gap-4">
          <HealthStatusPill />
        </div>
      </div>
    </nav>
  );
}
