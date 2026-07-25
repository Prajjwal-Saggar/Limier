"use client";

import { motion } from "framer-motion";
import { ReactNode } from "react";
import { Card } from "./ui/card";

interface StatCardProps {
  title: string;
  value: string | number | ReactNode;
  subtitle?: ReactNode;
  icon?: ReactNode;
  delay?: number;
}

export function StatCard({ title, value, subtitle, icon, delay = 0 }: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay, ease: [0.16, 1, 0.3, 1] }}
    >
      <Card className="h-full p-6 flex flex-col justify-between hover:bg-white/5 transition-colors duration-300 relative overflow-hidden group">
        <div className="absolute -inset-px bg-gradient-to-r from-primary/0 via-primary/10 to-primary/0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-xl pointer-events-none" />
        
        <div className="flex justify-between items-start mb-4">
          <h3 className="text-sm font-medium text-muted-foreground">{title}</h3>
          {icon && <div className="text-muted-foreground/50">{icon}</div>}
        </div>
        
        <div>
          <div className="text-3xl font-mono text-foreground mb-1">
            {value}
          </div>
          {subtitle && (
            <div className="text-xs text-muted-foreground mt-2">
              {subtitle}
            </div>
          )}
        </div>
      </Card>
    </motion.div>
  );
}
