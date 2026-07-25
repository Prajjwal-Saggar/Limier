"use client";

import { useEffect, useState } from "react";
import { checkHealth } from "@/lib/api";

export function HealthStatusPill() {
  const [healthy, setHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    let mounted = true;

    const check = async () => {
      try {
        await checkHealth();
        if (mounted) setHealthy(true);
      } catch (err) {
        if (mounted) setHealthy(false);
      }
    };

    // Check immediately
    check();
    
    // Poll every 30 seconds
    const interval = setInterval(check, 30000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-black/20 border border-white/5 backdrop-blur-sm">
      <div 
        className={`w-2 h-2 rounded-full shadow-[0_0_8px_currentColor] transition-colors duration-500 ${
          healthy === true ? "bg-primary text-primary" : healthy === false ? "bg-risk-high text-risk-high" : "bg-muted-foreground text-muted-foreground animate-pulse"
        }`} 
      />
      <span className="text-xs font-mono text-muted-foreground">
        {healthy === true ? "API CONNECTED" : healthy === false ? "API DISCONNECTED" : "CONNECTING..."}
      </span>
    </div>
  );
}
