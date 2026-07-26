"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Send, Bot, AlertTriangle, RefreshCw } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export interface ChatMessageData {
  id: string;
  role: "user" | "agent";
  text: string;
  isStreaming?: boolean;
  isError?: boolean;
  isRateLimit?: boolean;
}

interface ChatPanelProps {
  messages: ChatMessageData[];
  onSubmit: (query: string) => void;
  isLoading: boolean;
  lastQuery?: string;
}

export function ChatPanel({ messages, onSubmit, isLoading, lastQuery }: ChatPanelProps) {
  const [input, setInput] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSubmit(input);
    setInput("");
  };

  return (
    <div className="flex flex-col h-full bg-black/20 rounded-xl border border-white/5 backdrop-blur-md overflow-hidden">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-muted-foreground">
            <Bot className="w-12 h-12 mb-4 opacity-20" aria-hidden="true" />
            <p className="text-sm">Ask Limier to begin an investigation.</p>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} onRetry={msg.isRateLimit ? () => lastQuery && onSubmit(lastQuery) : undefined} />
            ))}
          </AnimatePresence>
        )}
        <div ref={endRef} />
      </div>

      <div className="p-4 bg-white/5 border-t border-white/5">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            id="agent-query-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask Limier... e.g. Is customer CUST_4521 suspicious?"
            disabled={isLoading}
            className="flex-1 bg-black/50 border-white/10 text-foreground placeholder:text-muted-foreground/50 focus-visible:ring-primary/50"
          />
          <Button
            type="submit"
            disabled={isLoading || !input.trim()}
            size="icon"
            className="shrink-0"
            aria-label="Send investigation query"
          >
            <Send className="w-4 h-4" aria-hidden="true" />
          </Button>
        </form>
      </div>
    </div>
  );
}

function ChatMessage({ message, onRetry }: { message: ChatMessageData; onRetry?: () => void }) {
  const isUser = message.role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}
    >
      <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${
        isUser
          ? "bg-primary text-black rounded-tr-sm"
          : message.isRateLimit
          ? "bg-amber-950/40 border border-amber-500/20 rounded-tl-sm text-foreground"
          : "glass rounded-tl-sm text-foreground"
      }`}>
        {message.isStreaming ? (
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 h-5">
              <span className="w-1.5 h-1.5 bg-current rounded-full animate-bounce [animation-delay:-0.3s]" />
              <span className="w-1.5 h-1.5 bg-current rounded-full animate-bounce [animation-delay:-0.15s]" />
              <span className="w-1.5 h-1.5 bg-current rounded-full animate-bounce" />
            </div>
            <span className="text-xs text-muted-foreground">Thinking...</span>
          </div>
        ) : message.isRateLimit ? (
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2 text-amber-400">
              <AlertTriangle className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span className="font-medium text-xs">Agent temporarily unavailable (rate limit)</span>
            </div>
            <p className="text-xs text-muted-foreground">The LLM API rate limit was reached. Please wait a moment and retry.</p>
            {onRetry && (
              <button
                onClick={onRetry}
                className="flex items-center gap-1.5 text-xs text-amber-400 hover:text-amber-300 transition-colors mt-1"
                aria-label="Retry the previous query"
              >
                <RefreshCw className="w-3 h-3" />
                Retry
              </button>
            )}
          </div>
        ) : (
          <div className="prose prose-sm prose-invert max-w-none leading-relaxed">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.text}</ReactMarkdown>
          </div>
        )}
      </div>
    </motion.div>
  );
}
