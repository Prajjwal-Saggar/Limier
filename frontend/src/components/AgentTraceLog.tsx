"use client";

import { AgentEvent } from "@/lib/types";
import { motion } from "framer-motion";
import { Check, Loader2, Bot, Wrench, Search, AlertTriangle } from "lucide-react";
import { useState, useEffect } from "react";

interface AgentTraceLogProps {
  events: AgentEvent[];
}

export function AgentTraceLog({ events }: AgentTraceLogProps) {
  if (events.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-center p-8 text-muted-foreground">
        <Bot className="w-12 h-12 mb-4 opacity-20" />
        <h3 className="font-display text-lg mb-2 text-foreground">Waiting for Instructions</h3>
        <p className="text-sm max-w-sm opacity-60">The AI investigator is idle. Ask a question to begin tracing its reasoning and actions.</p>
      </div>
    );
  }

  return (
    <div className="relative pl-6 space-y-8 py-4 before:absolute before:inset-0 before:ml-8 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-white/10 before:to-transparent">
      {events.map((ev, index) => (
        <TraceEvent key={index} event={ev} index={index} isLast={index === events.length - 1} />
      ))}
    </div>
  );
}

function TraceEvent({ event, index, isLast }: { event: AgentEvent, index: number, isLast: boolean }) {
  const isRunning = isLast && event.type === "tool_call";
  
  const getIcon = () => {
    switch (event.type) {
      case "intent_detected": return <Search className="w-4 h-4 text-primary" />;
      case "tool_call": return isRunning ? <Loader2 className="w-4 h-4 text-primary animate-spin" /> : <Wrench className="w-4 h-4 text-muted-foreground" />;
      case "tool_result": return <Check className="w-4 h-4 text-primary" />;
      case "error": return <AlertTriangle className="w-4 h-4 text-risk-high" />;
      case "final_answer": return <Bot className="w-4 h-4 text-primary" />;
      default: return <div className="w-2 h-2 rounded-full bg-muted-foreground" />;
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.1 }}
      className="relative flex items-start gap-6"
    >
      <div className="absolute left-0 w-5 h-5 rounded-full bg-black border-2 border-white/10 flex items-center justify-center z-10 -ml-2.5 mt-0.5 shadow-[0_0_10px_rgba(0,0,0,0.5)]">
        {getIcon()}
      </div>
      
      <div className="flex-1 glass-panel rounded-lg p-4 text-sm border-white/5">
        {event.type === "intent_detected" && (
          <div>
            <div className="text-xs uppercase tracking-widest text-primary mb-1">Intent Parsed</div>
            <div className="text-muted-foreground">Interpreting query: "{event.data.query}"</div>
          </div>
        )}
        
        {event.type === "tool_call" && (
          <div className={isRunning ? "animate-pulse" : ""}>
            <div className="text-xs uppercase tracking-widest text-muted-foreground mb-1">Calling Tool</div>
            <div className="font-mono text-primary/80">{event.data.tool}</div>
            {Object.keys(event.data.arguments || {}).length > 0 && (
              <pre className="mt-2 text-xs text-muted-foreground/70 bg-black/40 p-2 rounded">
                {JSON.stringify(event.data.arguments, null, 2)}
              </pre>
            )}
          </div>
        )}

        {event.type === "tool_result" && (
          <div>
            <div className="text-xs uppercase tracking-widest text-primary mb-1">Tool Completed</div>
            <div className="text-muted-foreground">Received response from <span className="font-mono">{event.data.tool}</span></div>
          </div>
        )}

        {event.type === "error" && (
          <div>
            <div className="text-xs uppercase tracking-widest text-risk-high mb-1">Error</div>
            <div className="text-risk-high">{event.data.message}</div>
          </div>
        )}

        {event.type === "final_answer" && (
          <div>
            <div className="text-xs uppercase tracking-widest text-primary mb-1">Analysis Complete</div>
            <div className="text-foreground">Sent response to user.</div>
          </div>
        )}
      </div>
    </motion.div>
  );
}
