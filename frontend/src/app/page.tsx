"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { fetchEda } from "@/lib/api";
import { streamAgentQuery } from "@/lib/streamClient";
import { EdaResponse, AgentEvent, ScoreResponse } from "@/lib/types";

import { StatCard } from "@/components/StatCard";
import { ChatPanel, ChatMessageData } from "@/components/ChatPanel";
import { AgentTraceLog } from "@/components/AgentTraceLog";
import { RiskTable } from "@/components/RiskTable";
import { EdaOverview } from "@/components/EdaOverview";
import { CustomerRiskDrawer } from "@/components/CustomerRiskDrawer";
import { Skeleton } from "@/components/ui/skeleton";
import { StatBar } from "@/components/StatBar";
import { ArchPillars } from "@/components/ArchPillars";
import { Users, Activity, Globe, ShieldAlert, Loader2 } from "lucide-react";
import { motion } from "framer-motion";

export default function Home() {
  const [edaData, setEdaData] = useState<EdaResponse | null>(null);
  const [edaLoading, setEdaLoading] = useState(true);

  const [messages, setMessages] = useState<ChatMessageData[]>([]);
  const [traceEvents, setTraceEvents] = useState<AgentEvent[]>([]);
  const [isAgentLoading, setIsAgentLoading] = useState(false);
  const [flaggedItems, setFlaggedItems] = useState<ScoreResponse[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<ScoreResponse | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const dashboardRef = useRef<HTMLDivElement>(null);
  const [lastQuery, setLastQuery] = useState<string>("");

  useEffect(() => {
    async function loadEda() {
      try {
        const data = await fetchEda();
        setEdaData(data);
      } catch (e) {
        console.error("Failed to load EDA stats", e);
      } finally {
        setEdaLoading(false);
      }
    }
    loadEda();
  }, []);

  const handleAgentQuery = async (query: string) => {
    const userMsg: ChatMessageData = { id: Date.now().toString(), role: "user", text: query };
    setMessages(prev => [...prev, userMsg]);
    setIsAgentLoading(true);
    setTraceEvents([]);
    setLastQuery(query);
    
    // Create placeholder agent message that shows typing indicator
    const agentMsgId = (Date.now() + 1).toString();
    setMessages(prev => [...prev, { id: agentMsgId, role: "agent", text: "", isStreaming: true }]);

    try {
      // Consume SSE stream
      const history = [...messages, userMsg].map(m => ({
        role: m.role === "agent" ? "assistant" : "user",
        content: m.text
      }));
      for await (const event of streamAgentQuery(history)) {
        setTraceEvents(prev => [...prev, event]);
        
        if (event.type === "final_answer") {
          // Replace typing indicator with final answer
          setMessages(prev => prev.map(m => m.id === agentMsgId ? { id: agentMsgId, role: "agent", text: event.data.text, isStreaming: false } : m));
          
          if (event.data.flagged_items && Array.isArray(event.data.flagged_items)) {
            setFlaggedItems(event.data.flagged_items);
            // Scroll down to table slightly if there are results
            setTimeout(() => {
              document.getElementById("results-table")?.scrollIntoView({ behavior: "smooth", block: "start" });
            }, 500);
          }
        }
        
        if (event.type === "error") {
          const errMsg = event.data?.message || "Unknown error";
          const isRateLimit = errMsg.includes("429") || errMsg.toLowerCase().includes("rate_limit") || errMsg.toLowerCase().includes("rate limit");
          setMessages(prev => prev.map(m =>
            m.id === agentMsgId
              ? { id: agentMsgId, role: "agent", text: errMsg, isStreaming: false, isError: true, isRateLimit }
              : m
          ));
        }
      }
    } catch (e: any) {
      const errMsg = e.message || "Unknown error";
      const isRateLimit = errMsg.includes("429") || errMsg.toLowerCase().includes("rate_limit") || errMsg.toLowerCase().includes("rate limit");
      setMessages(prev => prev.map(m =>
        m.id === agentMsgId
          ? { id: agentMsgId, role: "agent", text: errMsg, isStreaming: false, isError: true, isRateLimit }
          : m
      ));
    } finally {
      setIsAgentLoading(false);
    }
  };

  const handleViewCustomer = (customer: ScoreResponse) => {
    setSelectedCustomer(customer);
    setIsDrawerOpen(true);
  };

  // Demo CTA: pre-seeds the investigation with a default query and scrolls to the console
  const handleRunDemo = useCallback(() => {
    dashboardRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    setTimeout(() => {
      handleAgentQuery("Show me the top 5 most suspicious customers and generate a SAR for the highest risk one.");
    }, 600);
  }, [handleAgentQuery]);

  return (
    <div>
      {/* Landing Section (Item 7) */}
      <div className="max-w-7xl mx-auto">
        <ArchPillars onRunDemo={handleRunDemo} />
      </div>

      {/* Dashboard */}
      <div id="dashboard" ref={dashboardRef} className="max-w-7xl mx-auto px-6 py-8">

        {/* Hero Stat Cards — now inside dashboard section, not the landing hero */}
        <section className="mb-12">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {edaLoading ? (
            Array(4).fill(0).map((_, i) => <Skeleton key={i} className="h-[120px] rounded-xl" />)
          ) : edaData ? (
            <>
              <StatCard 
                title="Total Customers" 
                value={edaData.total_customers.toLocaleString()} 
                icon={<Users className="w-5 h-5" />} 
                delay={0.1}
              />
              <StatCard 
                title="Total Transactions" 
                value={edaData.total_transactions.toLocaleString()} 
                icon={<Activity className="w-5 h-5" />} 
                delay={0.2}
              />
              <StatCard 
                title="Cross-Border %" 
                value={`${(edaData.cross_border_pct * 100).toFixed(1)}%`} 
                icon={<Globe className="w-5 h-5" />} 
                delay={0.3}
              />
              <StatCard 
                title="Risk Breakdown" 
                value={<StatBar 
                  low={edaData.risk_level_breakdown.low}
                  medium={edaData.risk_level_breakdown.medium}
                  high={edaData.risk_level_breakdown.high}
                  className="h-6 mt-1 w-[80%]"
                />} 
                subtitle={
                  <div className="flex gap-3 text-xs mt-1 font-mono">
                    <span className="text-risk-low">{edaData.risk_level_breakdown.low} L</span>
                    <span className="text-risk-medium">{edaData.risk_level_breakdown.medium} M</span>
                    <span className="text-risk-high">{edaData.risk_level_breakdown.high} H</span>
                  </div>
                }
                icon={<ShieldAlert className="w-5 h-5" />} 
                delay={0.4}
              />
            </>
          ) : (
            <div className="col-span-4 p-4 text-center text-risk-high border border-risk-high/30 rounded-xl bg-risk-high/10">
              Failed to load dataset overview. Backend might be unreachable.
            </div>
          )}
        </div>
      </section>

      {/* Investigation Panel */}
      <section className="mb-16">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center border border-primary/30">
            <div className="w-2 h-2 bg-primary rounded-full animate-pulse" />
          </div>
          <h2 className="text-2xl font-display font-medium">Investigation Console</h2>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[600px]">
          <ChatPanel messages={messages} onSubmit={handleAgentQuery} isLoading={isAgentLoading} lastQuery={lastQuery} />
          
          <div className="bg-black/20 rounded-xl border border-white/5 backdrop-blur-md overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-white/5 bg-white/5 flex items-center justify-between">
              <h3 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">Live Agent Trace</h3>
            </div>
            <div className="flex-1 overflow-y-auto p-2">
              <AgentTraceLog events={traceEvents} />
            </div>
          </div>
        </div>
      </section>

      {/* Results Table */}
      <section id="results-table" className="mb-16 scroll-mt-24">
        <h2 className="text-2xl font-display font-medium mb-6">Flagged Entities</h2>
        {flaggedItems.length > 0 ? (
          <RiskTable data={flaggedItems} onViewDetails={handleViewCustomer} />
        ) : isAgentLoading ? (
          <div className="flex flex-col space-y-3">
            <Skeleton className="h-16 w-full rounded-xl" />
            <Skeleton className="h-16 w-full rounded-xl" />
            <Skeleton className="h-16 w-full rounded-xl" />
          </div>
        ) : (
          <div className="p-12 text-center text-muted-foreground border border-white/5 rounded-xl bg-black/20 backdrop-blur-md">
            No entities flagged yet. Run an investigation to see results.
          </div>
        )}
      </section>

      {/* EDA Section */}
      <section className="mb-8">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        >
          <h2 className="text-2xl font-display font-medium mb-2">Dataset Overview</h2>
          <p className="text-muted-foreground mb-6">Global patterns across the synthetic portfolio.</p>
        </motion.div>

        {edaLoading ? (
          <div className="h-64 rounded-xl border border-white/5 bg-black/20 backdrop-blur-md flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          >
            <EdaOverview data={edaData} />
          </motion.div>
        )}
      </section>

      {/* Drawer */}
      <CustomerRiskDrawer
        open={isDrawerOpen}
        onOpenChange={setIsDrawerOpen}
        customer={selectedCustomer}
      />
      </div>
    </div>
  );
}
