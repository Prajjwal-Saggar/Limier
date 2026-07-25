"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Send, Bot } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export interface ChatMessageData {
  id: string;
  role: "user" | "agent";
  text: string;
  isStreaming?: boolean;
}

interface ChatPanelProps {
  messages: ChatMessageData[];
  onSubmit: (query: string) => void;
  isLoading: boolean;
}

export function ChatPanel({ messages, onSubmit, isLoading }: ChatPanelProps) {
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
            <Bot className="w-12 h-12 mb-4 opacity-20" />
            <p className="text-sm">Ask Limier to begin an investigation.</p>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
          </AnimatePresence>
        )}
        <div ref={endRef} />
      </div>

      <div className="p-4 bg-white/5 border-t border-white/5">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask Limier... e.g. Is customer CUST_4521 suspicious?"
            disabled={isLoading}
            className="flex-1 bg-black/50 border-white/10 text-foreground placeholder:text-muted-foreground/50 focus-visible:ring-primary/50"
          />
          <Button type="submit" disabled={isLoading || !input.trim()} size="icon" className="shrink-0">
            <Send className="w-4 h-4" />
          </Button>
        </form>
      </div>
    </div>
  );
}

function ChatMessage({ message }: { message: ChatMessageData }) {
  const isUser = message.role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}
    >
      <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${isUser ? "bg-primary text-black rounded-tr-sm" : "glass rounded-tl-sm text-foreground"}`}>
        {message.isStreaming ? (
          <div className="flex items-center gap-1 h-5">
            <span className="w-1.5 h-1.5 bg-current rounded-full animate-bounce [animation-delay:-0.3s]" />
            <span className="w-1.5 h-1.5 bg-current rounded-full animate-bounce [animation-delay:-0.15s]" />
            <span className="w-1.5 h-1.5 bg-current rounded-full animate-bounce" />
          </div>
        ) : (
          <div className="whitespace-pre-wrap leading-relaxed">
            {formatMessage(message.text)}
          </div>
        )}
      </div>
    </motion.div>
  );
}

// Simple bolding formatter since we aren't pulling in a full markdown parser
function formatMessage(text: string) {
  const parts = text.split(/(\*\*.*?\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i} className="font-semibold text-primary/90">{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}
